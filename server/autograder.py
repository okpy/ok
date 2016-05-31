"""autograder.py: An interface to the autograder infrastructure (named autopy)

This module interfaces the OK Server with Autopy. The actual autograding happens
in a sandboxed environment.
"""

from flask import session, url_for
import requests

import server.constants as constants
from server.models import db, User, Assignment, Backup, Course, Enrollment
from server.extensions import cache
import server.utils as utils


def autograde_assignment(assignment, key, token, autopromotion=True):
    students, submissions, no_submissions = assignment.course_submissions()

    backups_to_grade = [utils.encode_id(bid) for bid in submissions]

    if autopromotion:
        # Hunt for backups from those with no_submissions
        seen = set()
        for student_uid in no_submissions:
            if student_uid not in seen:
                found_backup = assignment.backups([student_uid]).first()
                if found_backup:
                    seen |= found_backup.owners()
                    backups_to_grade.append(utils.encode_id(found_backup.id))

    data = {
        'subm_ids': backups_to_grade,
        'assignment': key,
        'access_token': token,
        'priority': 'normal',
        'ok-server-version': 'v3',
        'testing': token == 'testing',
    }
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    r = requests.post(constants.AUTOGRADER_URL+'/api/ok/v3/grade/batch',
                  data=json.dumps(data), headers=headers)

    if r.status_code == requests.codes.ok:
      return {'status': True, 'message': 'OK' }
    else:
      error_message = 'The autograder rejected your request. {}'.format(r.text)
      raise ValueError(error_message)



def submit_single(assignment, backup):
    email = backup.submitter.email
    file_contents = [b for b in backup.messages if b.kind == 'file_contents']
    if not file_contents:
        raise ValueError("No files to grade")

    data = {
        'assignment': assignment.autograding_key,
        'file_contents': file_contents[0],
        'submitter': email
        'emails': [User.email_by_id(oid) for oid in backup.owners()]
    }

    if not backup.submitter.is_enrolled(assignment.course_id):
        raise ValueError("User is not enrolled and cannot be autograded")

    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    r = requests.post(AUTOGRADER_URL+'/api/file/grade/continous',
        data=json.dumps(data), headers=headers)

    if r.status_code == requests.codes.ok:
        return {'status': "pending"}
    else:
        raise ValueError('The autograder the rejected your request')
