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

@cache.memoize(60)
def make_github_req(url, access_token):
    r = requests.get(url, headers={"Authorization": "Bearer {}".format(access_token)})
    r.raise_for_status()
    return r.json()

@cache.memoize(300)
def search_request(search_line, language, logger, access_token, page=1):
    """ Query https://api.github.com/search/code """
    try:
        search_query = ('"{line}" in:file language:{lang}'
                        .format(line=search_line, lang=language))

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
        print(e)
        return e

def get_all_results(search_line, language, logger, access_token):
    logger.info("Performing search for {}".format(search_line))
    first_req = search_request(search_line, language, logger, access_token)
    total_count = first_req.get('total_count')
    if not total_count:
        logger.warning("Failure to perform first search {}".format(first_req))
    logger.info("Repos Found {}".format(total_count))
    pages = range(2, math.ceil(total_count/50)+1)
    data_set = first_req['items']
    for page_num in pages:
        results = search_request(search_line, language, logger, access_token,
                                 page=page_num)
        if 'items' not in results:
            logging.warning("Req {} failed {}".format(page_num, results))
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

def get_recent_repos(repos, logger, access_token, weeks_past=12):
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
            owner = make_github_req(details['repository']['owner']['url'])
            if not owner['name']:
                owner['name'] = "@{}".format(owner['login'])
            if not owner['email']:
                owner['email'] = ""

            issue_repos[repo] = details
            user_details = "{} ({})".format(owner['name'], owner['email'])
            logger.info("{}: {} - {}".format(user_details, html_url,
                                             time_update.humanize()))
        seen_repos.add(details['repository']['html_url'])
    return issue_repos

def get_online_repos(source, language, logger, access_token,
                     keyword='def '):
    longest_lines = get_longest_defs(source, keyword)
    source = [get_all_results(longest_lines[i]) for i in range(3)]
    repos = OrderedDict()
    for repo in source:
        repos[repo['html_url']] = repo
    return repos


@jobs.background_job
def search_similar_repos(access_token=None, assignment_id=None, language=None,
                         keyword='def '):
    logger = jobs.get_job_logger()
    logger.info('Starting Github Search...')

    assign = Assignment.query.filter_by(id=assignment_id).one_or_none()
    if not assign:
        logger.info("Could not find assignment")
        return
    if not assign.files:
        logger.info("Upload template files for this assignment to search.")
        return
    # TODO: Call approriate functions
    
