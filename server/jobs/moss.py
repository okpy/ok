import os
import subprocess
import shlex
import glob
import tempfile
import re
import difflib
import socket
import requests
from html.parser import HTMLParser

from server.models import Assignment, Backup, MossResult, db
from server.utils import encode_id, decode_id
from server import jobs

def moss_submit(moss_id, submissions, ref_submissions, language,
            template_files=None, max_matches=10, file_regex='.*'):
    """ Sends SUBMISSIONS and REF_SUBMISSIONS to Moss using MOSS_ID,
    LANGUAGE, and MAX_MATCHES.
    Stores results involving SUBMISSIONS in database.
    """
    match_pattern = re.compile(file_regex)
    logger = jobs.get_job_logger()
    logger.info('Connecting to Moss...')
    moss = socket.socket()
    moss.connect(('moss.stanford.edu', 7690))
    moss.send('moss {}\n'.format(moss_id).encode())
    moss.send('directory 1\n'.encode())
    moss.send('X 0\n'.encode())
    moss.send('maxmatches {}\n'.format(max_matches).encode())
    moss.send('show 250\n'.encode())
    moss.send('language {}\n'.format(language).encode())
    lang_check = moss.recv(1024).decode().strip()
    if lang_check != 'yes':
        moss.close()
        logger.info('Invalid language {}. Job cancelled.'.format(language))
        return

    subm_keys = set()
    hashed_subm_keys = set()
    for subm in submissions:
        subm_keys.add(subm['backup']['id'])
        hashed_subm_keys.add(encode_id(subm['backup']['id']))
    for subm in ref_submissions:
        subm_keys.add(subm['backup']['id'])

    backup_query = (Backup.query.options(db.joinedload('messages'))
                          .filter(Backup.id.in_(subm_keys))
                          .order_by(Backup.created.desc())
                          .all())
    if template_files:
        logger.info('Uploading template...')
        for filename in template_files:
            contents = template_files[filename]
            send_file(moss, filename, contents, 0, language)
    fid = 0
    logger.info('Uploading submissions...')
    for backup in backup_query:
        file_contents = [m for m in backup.messages if m.kind == 'file_contents']
        if not file_contents:
            logger.info("{} didn't have any file contents".format(backup.hashid))
            continue
        contents = file_contents[0].contents
        for filename in contents:
            if filename == 'submit' or not match_pattern.match(filename):
                continue
            fid += 1
            path = os.path.join(backup.hashid, filename)
            send_file(moss, path, contents[filename], fid, language)
    moss.send("query 0 Submitted via okpy.org\n".encode())
    logger.info('Awaiting response...')
    url = moss.recv(1024).decode().strip()
    moss.send("end\n".encode())
    moss.close()
    logger.info('Moss results at: {}'.format(url))
    parse_moss_results(url, hashed_subm_keys, logger)

def parse_moss_results(base_url, hashed_ids, logger):
    match = 0
    while True:
        r = requests.get('{}/match{}-top.html'.format(base_url, match))
        if r.status_code == 404:
            logger.info('Finished parsing {} results.'.format(match))
            break
        match += 1
        parser = MossParser()
        parser.feed(r.content.decode())
        hashidA, hashidB = parser.ids
        if hashed_ids and hashidA not in hashed_ids and hashidB not in hashed_ids:
            logger.info('Skipping Moss result #{}.'.format(match))
            continue
        similarityA, similarityB = parser.similarities
        rangesA, rangesB = parser.ranges[::2], parser.ranges[1::2]
        matchesA = [[int(i) for i in r.split('-')] for r in rangesA]
        matchesB = [[int(i) for i in r.split('-')] for r in rangesB]
        submissionA = Backup.query.filter_by(id=decode_id(hashidA)).one_or_none()
        submissionB = Backup.query.filter_by(id=decode_id(hashidB)).one_or_none()
        resultA = MossResult.query.filter_by(submissionA=submissionA, submissionB=submissionB,
            similarityA=similarityA, similarityB=similarityB,
            matchesA=matchesA, matchesB=matchesB)
        resultB = MossResult.query.filter_by(submissionB=submissionA, submissionA=submissionB,
            similarityB=similarityA, similarityA=similarityB,
            matchesB=matchesA, matchesA=matchesB)
        if resultA or resultB:
            logger.info('Moss result #{} already exists.'.format(match))
            continue
        result = MossResult(submissionA=submissionA, submissionB=submissionB,
            similarityA=similarityA, similarityB=similarityB,
            matchesA=matchesA, matchesB=matchesB)
        db.session.add(result)
        logger.info('Adding Moss result #{}...'.format(match))
    db.session.commit()
    moss_results = MossResult.query.all()
    logger.info('Total: {}'.format(len(moss_results)))

class MossParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.last_start = None
        self.ids = []
        self.similarities = []
        self.ranges = []
    def handle_starttag(self, tag, attrs):
        self.last_start = tag
    def handle_data(self, data):
        data = data.strip()
        if self.last_start == 'th' and data:
            ident, percent = data.split('/ (')
            self.ids.append(ident)
            self.similarities.append(int(percent[:-2]))
        elif self.last_start == 'a' and data:
            self.ranges.append(data)


def send_file(moss, path, contents, fid, language):
    size = len(contents.encode())
    path = path.replace(' ', '_')
    header = "file {} {} {} {}\n".format(fid, language, size, path)
    msg = header + contents
    moss.send(msg.encode())

@jobs.background_job
def submit_to_moss(moss_id=None, file_regex=".*", assignment_id=None, language=None,
                   subtract_template=False):
    assign = Assignment.query.filter_by(id=assignment_id).one_or_none()
    if not assign:
        raise Exception("Could not find assignment")
    subms = assign.course_submissions(include_empty=False)
    template = {}
    if not subtract_template and assign.files:
        for filename in assign.files:
            template[filename] = assign.files[filename]
    return moss_submit(moss_id, subms, [], language, template, 10, file_regex)

@jobs.background_job
def parse_moss_job(base_url, hashed_ids=None):
    parse_moss_results(base_url, hashed_ids, jobs.get_job_logger())
