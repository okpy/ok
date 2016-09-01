"""autograder.py: An interface to the autograder infrastructure (named autopy)

This module interfaces the OK Server with Autopy. The actual autograding happens
in a sandboxed environment.
"""

from flask import url_for
import json
import requests
import logging

import server.constants as constants
from server.models import User, Backup, db
import server.utils as utils

logger = logging.getLogger(__name__)

def send_autograder(endpoint, data):
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    r = requests.post(constants.AUTOGRADER_URL + endpoint,
                      data=json.dumps(data), headers=headers, timeout=8)

    if r.status_code == requests.codes.ok:
        return {'status': True, 'message': 'OK'}
    else:
        error_message = 'The autograder rejected your request. {0}'.format(
            r.text)
        logger.debug('Autograder {} response: {}'.format(r.status_code,
                                                         error_message))
        raise ValueError(error_message)

def autograde_assignment(assignment, ag_assign_key, token, autopromotion=True):
    """ Autograde all enrolled students for this assignment.
    If ag_assign_key is 'test', the autograder will respond with 'OK' but not grade.

    @assignment: Assignment object.
    @ag_assign_key: Autograder ID (from Autograder Dashboard)
    @token: OK Access Token (from auth)
    """
    course_submissions = assignment.course_submissions(include_empty=False)
    submissions = [fs['backup'] for fs in course_submissions if fs['backup']]
    submissions_id = set(utils.encode_id(fs['id']) for fs in submissions)

    if autopromotion:
        # Change FS backups into submissions
        for fs in submissions:
            if not fs['submit']:
                backup = Backup.query.get(fs['id'])
                backup.submit = True
        db.session.commit()

    data = {
        'subm_ids': submissions_id,
        'assignment': ag_assign_key,
        'access_token': token,
        'priority': 'default',
        'backup_url': url_for('api.backup', _external=True),
        'ok-server-version': 'v3',
        'testing': token == 'testing',
    }
    return send_autograder('/api/ok/v3/grade/batch', data)

def grade_single(backup, ag_assign_key, token):

    data = {
        'subm_ids': [utils.encode_id(backup.id)],
        'assignment': ag_assign_key,
        'access_token': token,
        'priority': 'default',
        'backup_url': url_for('api.backup', _external=True),
        'ok-server-version': 'v3',
        'testing': token == 'testing',
    }
    return send_autograder('/api/ok/v3/grade/batch', data)

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
