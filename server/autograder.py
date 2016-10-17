"""autograder.py: An interface to the autograder infrastructure (named autopy)

This module interfaces the OK Server with Autopy. The actual autograding happens
in a sandboxed environment.
"""

from flask import url_for
from flask_login import current_user
import datetime
import json
import requests
import logging
import oauthlib.common

import server.constants as constants
from server.models import User, Backup, Client, Token, db
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

def send_batch(assignment, backup_ids):
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

    return send_autograder('/api/ok/v3/grade/batch', {
        'subm_ids': [utils.encode_id(bid) for bid in backup_ids],
        'assignment': assignment.autograding_key,
        'access_token': token.access_token,
        'priority': 'default',
        'backup_url': url_for('api.backup', _external=True),
        'ok-server-version': 'v3',
    })

def autograde_assignment(assignment):
    """Autograde all enrolled students for this assignment.

    @assignment: Assignment object
    """
    course_submissions = assignment.course_submissions(include_empty=False)
    backup_ids = set(fs['backup']['id'] for fs in course_submissions if fs['backup'])
    return send_batch(assignment, backup_ids)

def autograde_backup(backup):
    return send_batch(backup.assignment, [backup.id])

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
