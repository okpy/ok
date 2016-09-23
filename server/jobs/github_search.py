""" Script to search for similiar files on github """
import os
import requests
import math
import logging
import functools
import tempfile
import time
from collections import OrderedDict

import arrow

from server.models import Assignment, Backup, db
from server.utils import encode_id
from server.extensions import cache
from server import jobs

def get_file_from_github(html_url, logger):
    """ Github HTML url to raw url with github """
    # return html_url.replace('http://github.com/', 'https://raw.githubusercontent.com/')
    html_url = html_url.replace('/blob', '')
    return html_url.replace('https://github.com/', 'http://rawgit.com/')

    try:
        get = requests.get(html_url)
        get.raise_for_status()
        return get.text
    except requests.exceptions.RequestException as e:
        logger.warning("Failed to fetch {} - {}".format(html_url, e))

def make_github_req(url, access_token):
    r = requests.get(url, headers={"Authorization": "Bearer {}".format(access_token)})
    r.raise_for_status()
    return r.json()

def search_request(search_line, language, logger, access_token, page=1):
    """ Query https://api.github.com/search/code """
    search_query = ('"{line}" in:file language:{lang}'
                    .format(line=search_line, lang=language))
    if page > 6:
        logger.info("Stopping at page 6")
        return []
    try:
        response = requests.get(
            url="https://api.github.com/search/code",
            params={
                "q": search_query,
                "page": "{}".format(page),
                "per_page": "50",
                "sort": "updated"
            },
            headers={
                "Authorization": "Bearer {}".format(access_token),
                # "Accept": "application/vnd.github.v3.text-match+json"
                # if partial text matches data is useful
            },
        )
        data = response.json()
        response.raise_for_status()
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset = response.headers.get('X-RateLimit-Reset')
        if not remaining and reset:
            seconds_wait = reset - time.gmtime()
            friendly_limit = arrow.utcnow().replace(seconds=seconds_wait * 5).humanize()
            logger.warning(("Rate limited on page {}. Quota refreshing {}"
                            .format(page, friendly_limit)))
            return []
        elif 'items' not in data:
            logger.warning("Could not query page {}: {}".format(page, data))
            return []
        return data
    except requests.exceptions.RequestException as e:
        if response.status_code == 403:
            logger.warning("No Token/Rate Limit: {}".format(response.text))
        logger.warning("HTTP Error when fetching {}: \n {}".format(search_query, e))
        return

def get_all_results(search_line, language, logger, access_token):
    logger.info("Performing search for {}".format(search_line))
    first_req = search_request(search_line, language, logger, access_token)
    if not first_req:
        logger.warning("Failure to perform first search")
        return
    total_count = first_req.get('total_count')
    if not total_count:
        logger.warning("There were no matching results on GitHub")
        return
    logger.info("Repos Found {}".format(total_count))
    pages = range(2, min(math.ceil(total_count/50)+1, 5))
    data_set = first_req['items']
    for page_num in pages:
        logger.info("Fetching page {}".format(page_num))
        time.sleep(8)
        results = search_request(search_line, language, logger, access_token,
                                 page=page_num)
        if not results or 'items' not in results:
            logging.warning("Request {} failed {}".format(page_num, results))
            return data_set
        else:
            data_set.extend(results['items'])
    return data_set

def download_repos(repos):
    """ For future use. """
    with tempfile.TemporaryDirectory() as tmp_dir:
        for url in repos:
            repo = repos[url]
            file_contents = get_file_from_github(url)
            file_name = repo['name']
            repo_name = repo['repository']['full_name']
            dest = "{}/{}/".format(tmp_dir, repo_name)
            if not os.path.exists(dest):
                os.makedirs(dest)
            with open(dest + file_name, 'w') as f:
                f.write(file_contents)

def get_longest_defs(source_file, keyword, num_results=5):
    defs = [d.strip() for d in source_file.split('\n') if d.startswith(keyword)]
    longest_defs = sorted(defs, key=lambda x: len(x), reverse=True)
    return longest_defs[0:num_results]

def list_recent_repos(repos, logger, access_token, weeks_past=12):
    issue_repos = OrderedDict()
    seen_repos = set()
    treshold_date = arrow.utcnow().replace(weeks=(-1 * weeks_past))
    for repo, details in repos.items():
        api_url = details['repository']['url']
        html_url = details['repository']['html_url']
        if html_url in seen_repos:
            continue
        updated_time = make_github_req(api_url, access_token)['pushed_at']
        time_update = arrow.get(updated_time)
        if time_update > treshold_date:
            owner = make_github_req(details['repository']['owner']['url'], access_token)
            if not owner['name']:
                owner['name'] = "@{}".format(owner['login'])
            if not owner['email']:
                owner['email'] = "?"

            issue_repos[repo] = details
            user_details = "{} ({})".format(owner['name'], owner['email'])
            logger.info("{}: {} - {}".format(user_details, html_url,
                                             time_update.humanize()))
        seen_repos.add(details['repository']['html_url'])
    return issue_repos

def get_online_repos(source, logger, language, access_token,
                     keyword='def '):
    longest_lines = get_longest_defs(source, keyword)
    if not longest_lines:
        logger.warning("'{}' not found in source file: {}".format(keyword, source))
        return
    else:
        logger.info("Found {} candidate lines".format(len(longest_lines)))
    source = []

    for i in range(min(2, len(longest_lines))):
        logger.info("Fetching query {}".format(i))
        res = get_all_results(longest_lines[i], language, logger, access_token)
        source.extend(res)
        time.sleep(9)

    repos = OrderedDict()
    for repo in source:
        if not repo:
            continue
        else:
            repos[repo['html_url']] = repo
    return repos

@jobs.background_job
def search_similar_repos(access_token=None, assignment_id=None,
                         language='python', template_name=None,
                         keyword='def ', weeks_past=12):
    logger = jobs.get_job_logger()
    logger.info('Starting Github Search...')

    assign = Assignment.query.filter_by(id=assignment_id).one_or_none()
    if not assign:
        logger.info("Could not find assignment")
        return
    if not assign.files:
        logger.info("Upload template files for this assignment to search.")
        return

    possible_file_names = list(assign.files.keys())
    if template_name not in possible_file_names:
        logger.info("{} is not in {}".format(template_name, possible_file_names))

    source_file = assign.files[template_name]
    repos = get_online_repos(source_file, logger, language, access_token,
                             keyword=keyword)
    if not repos:
        logger.warning("No repos found. Try a different keyword?")
        return
    recent_repos = list_recent_repos(repos, logger, access_token, weeks_past)
