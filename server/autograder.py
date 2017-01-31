"""autograder.py: An interface to the autograder infrastructure (named autopy)

This module interfaces the OK Server with Autopy. The actual autograding happens
in a sandboxed environment.
"""
import collections
import enum
import time

from flask_login import current_user
import datetime
import json
import requests
import logging
import oauthlib.common

from server import constants, jobs, utils
from server.models import User, Assignment, Backup, Client, Score, Token, db

logger = logging.getLogger(__name__)

def send_autograder(endpoint, data):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    r = requests.post(constants.AUTOGRADER_URL + endpoint,
                      data=json.dumps(data), headers=headers, timeout=8)

    if r.status_code == requests.codes.ok:
        return r.json()
    else:
        error_message = 'The autograder rejected your request. {0}'.format(
            r.text)
        logger.debug('Autograder {} response: {}'.format(r.status_code,
                                                         error_message))
        raise ValueError(error_message)

def send_batch(assignment, backup_ids, priority='default'):
    """Send a batch of backups to the autograder, returning a dict mapping
    backup ID -> autograder job ID.
    """
    if not assignment.autograding_key:
        raise ValueError('Assignment has no autograder key')

    # Create an access token for this run
    autograder_client = Client.query.get('autograder')
    if not autograder_client:
        autograder_client = Client(
            name='Autograder',
            client_id='autograder',
            client_secret='autograder',
            redirect_uris=[],
            is_confidential=False,
            description='The Autopy autograder system',
            default_scopes=['all'],
        )
        db.session.add(autograder_client)
        db.session.commit()
    token = Token(
        client=autograder_client,
        user=current_user,
        token_type='bearer',
        access_token=oauthlib.common.generate_token(),
        expires=datetime.datetime.utcnow() + datetime.timedelta(hours=2),
        scopes=['all'],
    )
    db.session.add(token)
    db.session.commit()

    response_json = send_autograder('/api/ok/v3/grade/batch', {
        'subm_ids': [utils.encode_id(bid) for bid in backup_ids],
        'assignment': assignment.autograding_key,
        'access_token': token.access_token,
        'priority': priority,
        'ok-server-version': 'v3',
    })
    return dict(zip(backup_ids, response_json['jobs']))

def autograde_backup(backup):
    """Autograde a backup, returning and autograder job ID."""
    jobs = send_batch(backup.assignment, [backup], priority='high')
    return jobs[backup]

def submit_continous(backup):
    """ Intended for continous grading (email with results on submit)
    """
    email = backup.submitter.email
    assignment = backup.assignment
    file_contents = [b for b in backup.messages if b.kind == 'file_contents']
    if not file_contents:
        raise ValueError("No files to grade")
    if not assignment.autograding_key:
        raise ValueError("Not setup for autograding")

    data = {
        'assignment': assignment.autograding_key,
        'file_contents': file_contents[0].contents,
        'submitter': email,
        'emails': [User.email_by_id(oid) for oid in backup.owners()]
    }

    if not backup.submitter.is_enrolled(assignment.course_id):
        raise ValueError("User is not enrolled and cannot be autograded")

    return send_autograder('/api/file/grade/continous', data)

def check_job_results(job_ids):
    """Given a list of autograder job IDs, return a dict mapping job IDs to
    either null (if the job does not exist) of a dict with keys
        status: one of 'queued', 'finished', 'failed', 'started', 'deferred'
        result: string
    """
    return send_autograder('/results', job_ids)

GradingStatus = enum.Enum('GradingStatus', [
    'PENDING',  # a job is running
    'WAITING',  # the last job has finished, and we are waiting for a score
    'DONE',     # we have a score
    'FAILED',   # we could not get a score after several retries
])

class GradingTask:
    def __init__(self, status, backup_id, job_id, retries, start_time, end_time):
        self.status = status
        self.backup_id = backup_id
        self.job_id = job_id
        self.retries = retries
        self.start_time = start_time
        self.end_time = end_time

MAX_RETRIES = 3     # maximum number of times to retry a score
JOB_TIMEOUT = 10    # time to wait for an autograder job, in seconds
SCORE_TIMEOUT = 10  # time to wait for a score, in seconds
POLL_INTERVAL = 5   # how often to poll the autograder, in seconds

@jobs.background_job
def autograde_assignment(assignment_id):
    """Autograde all enrolled students for this assignment."""
    logger = jobs.get_job_logger()

    assignment = Assignment.query.get(assignment_id)
    course_submissions = assignment.course_submissions(include_empty=False)
    backup_ids = set(fs['backup']['id'] for fs in course_submissions if fs['backup'])

    # start by sending a batch of all backups
    start_time = time.time()
    job_ids = send_batch(assignment, backup_ids)
    tasks = [
        GradingTask(
            status=GradingStatus.PENDING,
            backup_id=backup_id,
            job_id=job_id,
            retries=0,
            start_time=start_time,
            end_time=None,
        )
        for backup_id, job_id in job_ids.items()
    ]

    def retry_task(task):
        if task.retries >= MAX_RETRIES:
            logger.error('Did not receive a score for backup {} after {} retries'.format(
                utils.encode_id(task.backup_id), MAX_RETRIES))
            task.status = GradingStatus.FAILED
        else:
            task.status = GradingStatus.PENDING
            task.job_id = autograde_backup(task.backup_id)
            task.retries += 1
            task.start_time = time.time()

    while True:
        time.sleep(POLL_INTERVAL)
        now = time.time()
        results = check_job_results(list(job_ids))

        done = True
        for task in tasks:
            hashid = utils.encode_id(task.backup_id)
            if task.status == GradingStatus.PENDING:
                done = False
                result = results[task.job_id]
                if result and result.status == 'finished':
                    logger.info('Autograder job {} for backup {} finished'.format(
                        task.job_id, hashid))
                    task.status = GradingStatus.WAITING
                    task.end_time = now
                elif now > task.start_time + JOB_TIMEOUT:
                    logger.warning('Autograder job {} took longer than {} seconds, retrying'.format(
                        task.job_id, JOB_TIMEOUT))
                    retry_task(task)
            elif task.status == GradingStatus.WAITING:
                done = False
                score = Score.query.filter_by(
                    Score.backup_id == task.backup_id,
                    Score.archived == False,
                    Score.created > datetime.datetime.fromtimestamp(start_time)
                ).first()
                if score:
                    logger.info('Received score for backup {}'.format(
                        hashid))
                    task.status = GradingStatus.DONE
                elif now > task.end_time + SCORE_TIMEOUT:
                    logger.warning('Did not receive score for backup {} in {} seconds, retrying'.format(
                        hashid, SCORE_TIMEOUT))
                    retry_task(task)
        if done:
            break

    # report summary
    statuses = collections.Counter(task.status for task in tasks)
    return '{} graded, {} failed'.format(
        statuses[GradingStatus.DONE], statuses[GradingStatus.FAILED])
