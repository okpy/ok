"""autograder.py: An interface to the autograder infrastructure (named autopy)

This module interfaces the OK Server with Autopy. The actual autograding happens
in a sandboxed environment.
"""
import collections
import datetime
import enum
import json
import logging
import time

import oauthlib.common
import requests

from server import constants, jobs, utils
from server.models import User, Assignment, Backup, Client, Score, Token, Course, db

logger = logging.getLogger(__name__)

def send_autograder(endpoint, data, autograder_url):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    r = requests.post(autograder_url + endpoint,
                      data=json.dumps(data), headers=headers, timeout=30)

    if r.status_code == requests.codes.ok:
        if r.text == "OK":  # e.g. when the token is "test"
            return None
        return r.json()
    else:
        error_message = 'The autograder rejected your request. {0}'.format(
            r.text)
        logger.debug('Autograder {} response: {}'.format(r.status_code,
                                                         error_message))
        raise ValueError(error_message)

def create_autograder_token(user_id):
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
        user_id=user_id,
        token_type='bearer',
        access_token=oauthlib.common.generate_token(),
        expires=datetime.datetime.utcnow() + datetime.timedelta(hours=2),
        scopes=['all'],
    )
    db.session.add(token)
    db.session.commit()
    return token

def send_batch(token, assignment, backup_ids, priority='default'):
    """Send a batch of backups to the autograder, returning a dict mapping
    backup ID -> autograder job ID.
    """
    if not assignment.autograding_key:
        raise ValueError('Assignment has no autograder key')

    response_json = send_autograder('/api/ok/v3/grade/batch', {
        'subm_ids': [utils.encode_id(bid) for bid in backup_ids],
        'assignment': assignment.autograding_key,
        'access_token': token.access_token,
        'priority': priority,
        'ok-server-version': 'v3',
    }, autograder_url=assignment.course.autograder_url)
    if response_json:
        return dict(zip(backup_ids, response_json['jobs']))
    else:
        return {}

def autograde_backup(token, assignment, backup_id):
    """Autograde a backup, returning and autograder job ID."""
    jobs = send_batch(token, assignment, [backup_id], priority='high')
    return jobs.get(backup_id)

def submit_continuous(backup):
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

    autograder_url = assignment.course.autograder_url

    if not backup.submitter.is_enrolled(assignment.course_id):
        raise ValueError("User is not enrolled and cannot be autograded")

    return send_autograder('/api/file/grade/continous', data, autograder_url=autograder_url)

def check_job_results(job_ids, autograder_url):
    """Given a list of autograder job IDs, return a dict mapping job IDs to
    either null (if the job does not exist) of a dict with keys
        status: one of 'queued', 'finished', 'failed', 'started', 'deferred'
        result: string
    """
    return send_autograder('/results', job_ids, autograder_url)

GradingStatus = enum.Enum('GradingStatus', [
    'QUEUED',   # a job is queued
    'RUNNING',  # a job is running
    'WAITING',  # the last job has finished, and we are waiting for a score
    'DONE',     # we have a score
    'FAILED',   # we could not get a score after several retries
])

class GradingTask:
    def __init__(self, status, backup_id, job_id, retries):
        self.status = status
        self.backup_id = backup_id
        self.job_id = job_id
        self.retries = retries
        self.status_change_time = time.time()

    def set_status(self, status):
        self.status = status
        self.status_change_time = time.time()

    def expired(self, timeout):
        """Returns True if it has been at least TIMEOUT seconds since the last
        status change.
        """
        return time.time() > self.status_change_time + timeout

MAX_RETRIES = 3           # maximum number of times to retry a score
QUEUED_TIMEOUT = 30 * 60  # maximum time or an autograder job to be queued for, in seconds
RUNNING_TIMEOUT = 5 * 60  # time to wait for an autograder job to run, in seconds
WAITING_TIMEOUT = 2 * 60  # time to wait for a score, in seconds
POLL_INTERVAL = 10        # how often to poll the autograder, in seconds

def autograde_backups(assignment, user_id, backup_ids, logger):
    token = create_autograder_token(user_id)

    start_time = time.time()
    job_ids = send_batch(token, assignment, backup_ids)
    tasks = [
        GradingTask(
            status=GradingStatus.QUEUED,
            backup_id=backup_id,
            job_id=job_id,
            retries=0,
        )
        for backup_id, job_id in job_ids.items()
    ]
    num_tasks = len(tasks)

    autograder_url = assignment.course.autograder_url

    def retry_task(task):
        if task.retries >= MAX_RETRIES:
            logger.error('Did not receive a score for backup {} after {} retries'.format(
                utils.encode_id(task.backup_id), MAX_RETRIES))
            task.set_status(GradingStatus.FAILED)
        else:
            task.set_status(GradingStatus.QUEUED)
            task.job_id = autograde_backup(token, assignment, task.backup_id)
            task.retries += 1

    while True:
        time.sleep(POLL_INTERVAL)
        results = check_job_results([task.job_id for task in tasks], autograder_url)

        graded = len([task for task in tasks
            if task.status in (GradingStatus.DONE, GradingStatus.FAILED)])
        logger.info('Graded {:>4}/{} ({:>5.1f}%)'.format(
            graded, num_tasks, 100 * graded / num_tasks))
        if graded == num_tasks:
            break

        for task in tasks:
            hashid = utils.encode_id(task.backup_id)
            if task.status == GradingStatus.QUEUED:
                result = results[task.job_id]
                if not result:
                    logger.warning('Autograder job {} for backup {} disappeared, retrying'.format(task.job_id, hashid))
                    retry_task(task)
                elif result['status'] != 'queued':
                    logger.debug('Autograder job {} for backup {} started'.format(
                        task.job_id, hashid))
                    task.set_status(GradingStatus.RUNNING)
                elif task.expired(QUEUED_TIMEOUT):
                    logger.warning('Autograder job {} for backup {} queued longer than {} seconds, retrying'.format(
                        task.job_id, hashid, QUEUED_TIMEOUT))
                    retry_task(task)
            elif task.status == GradingStatus.RUNNING:
                result = results[task.job_id]
                if not result:
                    logger.warning('Autograder job {} for backup {} disappeared, retrying'.format(task.job_id, hashid))
                    retry_task(task)
                elif result['status'] == 'finished':
                    logger.debug('Autograder job {} for backup {} finished'.format(
                        task.job_id, hashid))
                    task.set_status(GradingStatus.WAITING)
                elif result['status'] == 'failed':
                    logger.warning('Autograder job {} for backup {} failed, retrying'.format(task.job_id, hashid))
                    retry_task(task)
                elif task.expired(RUNNING_TIMEOUT):
                    logger.warning('Autograder job {} for backup {} running longer than {} seconds, retrying'.format(
                        task.job_id, hashid, RUNNING_TIMEOUT))
                    retry_task(task)
            elif task.status == GradingStatus.WAITING:
                score = Score.query.filter(
                    Score.backup_id == task.backup_id,
                    Score.archived == False,
                    Score.created > datetime.datetime.fromtimestamp(start_time)
                ).first()
                if score:
                    logger.debug('Received score for backup {}'.format(hashid))
                    task.set_status(GradingStatus.DONE)
                elif task.expired(WAITING_TIMEOUT):
                    logger.warning('Did not receive score for backup {} in {} seconds, retrying'.format(
                        hashid, WAITING_TIMEOUT))
                    retry_task(task)

    # report summary
    statuses = collections.Counter(task.status for task in tasks)
    message = '{} graded, {} failed'.format(
        statuses[GradingStatus.DONE], statuses[GradingStatus.FAILED])
    logger.info(message)


@jobs.background_job
def autograde_assignment(assignment_id):
    """Autograde all enrolled students for this assignment.

    We set up a state machine for each backup to check its progress through
    the autograder. If any step takes too long, we'll retry autograding that
    backup. Ultimately, a backup is considered done when we confirm that
    we've received a new score, or if we have reached the retry limit.
    """
    logger = jobs.get_job_logger()
    assignment = Assignment.query.get(assignment_id)
    course_submissions = assignment.course_submissions(include_empty=False)
    backup_ids = set(fs['backup']['id'] for fs in course_submissions if fs['backup'])
    try:
        autograde_backups(assignment, jobs.get_current_job().user_id, backup_ids, logger)
    except ValueError:
        logger.info('Could not autograde backups - Please add an autograding key.')
        return
    return '/admin/course/{cid}/assignments/{aid}/scores'.format(
                cid=jobs.get_current_job().course_id, aid=assignment.id)

