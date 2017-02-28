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
from server.highlight import highlight_diff
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
        merged_contents = ""
        for filename in template_files:
            if filename == 'submit' or not match_pattern.match(filename):
                continue
            merged_contents += template_files[filename] + '\n'
        send_file(moss, 'allcode', merged_contents, 0, language)
    fid = 0
    logger.info('Uploading submissions...')
    for backup in backup_query:
        file_contents = [m for m in backup.messages if m.kind == 'file_contents']
        if not file_contents:
            logger.info("{} didn't have any file contents".format(backup.hashid))
            continue
        contents = file_contents[0].contents
        merged_contents = ""
        for filename in sorted(contents.keys()):
            if filename == 'submit' or not match_pattern.match(filename):
                continue
            merged_contents += contents[filename] + '\n'
        fid += 1
        path = os.path.join(backup.hashid, 'allcode')
        send_file(moss, path, merged_contents, fid, language)
    moss.send("query 0 Submitted via okpy.org\n".encode())
    logger.info('Awaiting response...')
    url = moss.recv(1024).decode().strip()
    moss.send("end\n".encode())
    moss.close()
    logger.info('Moss results at: {}'.format(url))
    parse_moss_results(url, hashed_subm_keys, logger, match_pattern, template_files)

def parse_moss_results(base_url, hashed_ids, logger, pattern, template):
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
        matchesA = recalculate_lines(submissionA, matchesA, pattern)
        matchesB = recalculate_lines(submissionB, matchesB, pattern)
        similarityA = recalculate_similarity(submissionA, matchesA, template)
        similarityB = recalculate_similarity(submissionB, matchesB, template)
        resultA = MossResult.query.filter_by(submissionA=submissionA, submissionB=submissionB,
            similarityA=similarityA, similarityB=similarityB,
            matchesA=matchesA, matchesB=matchesB).one_or_none()
        resultB = MossResult.query.filter_by(submissionB=submissionA, submissionA=submissionB,
            similarityB=similarityA, similarityA=similarityB,
            matchesB=matchesA, matchesA=matchesB).one_or_none()
        if resultA or resultB:
            logger.info('Moss result #{} already exists.'.format(match))
            continue
        result = MossResult(submissionA=submissionA, submissionB=submissionB,
            similarityA=similarityA, similarityB=similarityB,
            matchesA=matchesA, matchesB=matchesB)
        db.session.add(result)
        logger.info('Adding Moss result #{}...'.format(match))
    db.session.commit()

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

def recalculate_lines(submission, raw_matches, pattern):
    files = submission.files()
    file_matches = {f:[] for f in files if pattern.match(f)}
    starts = {}
    current = 0
    for filename in sorted(file_matches.keys()):
        starts[current] = filename
        current += len(files[filename].split('\n'))
    def find_file(line):
        last_line = 0
        for start_line in starts:
            if line == start_line:
                return starts[start_line], start_line
            if line < start_line:
                return starts[last_line], last_line
            last_line = start_line
        return starts[last_line], last_line
    for match in raw_matches:
        start_file, sf_line = find_file(match[0])
        end_file, ef_line = find_file(match[1])
        if start_file == end_file:
            file_matches[start_file].append([x - sf_line for x in match])
        else:
            start_match = [match[0] - sf_line, len(files[filename].split('\n')) - 1]
            file_matches[start_file].append(start_match)
            end_match = [0, match[1] - ef_line]
            file_matches[end_file].append(end_match)
    return file_matches

def recalculate_similarity(submission, matches, template):
    student_lines, similar_student_lines = 0, 0
    files = submission.files()
    for filename in matches:
        student_code = files[filename]
        matched_lines = []
        for m in matches[filename]:
            matched_lines += list(range(m[0], m[1] + 1))
        matched_lines = set(matched_lines)
        template_code = template[filename] if filename in template else ""
        for line in highlight_diff(filename, template_code, student_code):
            if line.tag == 'insert':
                student_lines += 1
                if line.line_after in matched_lines:
                    similar_student_lines += 1
    return round(similar_student_lines * 100 / student_lines)

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
def parse_moss_job(base_url, hashed_ids=None, file_regex='.*', template={}):
    parse_moss_results(base_url, hashed_ids, jobs.get_job_logger(),
                       sre.compile(file_regex), template)
