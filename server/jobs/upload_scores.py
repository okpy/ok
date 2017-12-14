import os
from collections import defaultdict
from flask import url_for
from sqlalchemy.exc import SQLAlchemyError

import server

from server import jobs
from server.constants import STUDENT_ROLE
from server.models import Assignment, Enrollment, Backup, User, Score, db
from server.utils import send_email

from traceback import print_exc


@jobs.background_job
def score_from_csv(assign_id, rows, kind='total', invalid=None, message=None):
    """
    Job for uploading Scores.

    @param ``rows`` should be a list of records (mappings),
        with labels `email` and `score`
    """
    log = jobs.get_job_logger()
    current_user = jobs.get_current_job().user
    assign = Assignment.query.get(assign_id)

    message = message or '{} score for {}'.format(kind.title(), assign.display_name)

    def log_err(msg):
        log.info('\t!  {}'.format(msg))

    log.info("Uploading scores for {}:\n".format(assign.display_name))

    if invalid:
        log_err('skipping {} invalid entries on lines:'.format(len(invalid)))
        for line in invalid:
            log_err('\t{}'.format(line))
        log.info('')

    success, total = 0, len(rows)
    for i, row in enumerate(rows, start=1):
        try:
            email, score = row['email'], row['score']
            user = User.query.filter_by(email=email).one()

            backup = Backup.query.filter_by(assignment=assign, submitter=user, submit=True).first()
            if not backup:
                backup = Backup.create(submitter=user, assignment=assign, submit=True)

            uploaded_score = Score(grader=current_user, assignment=assign,
                    backup=backup, user=user, score=score, kind=kind, message=message)

            db.session.add(uploaded_score)
            uploaded_score.archive_duplicates()

        except SQLAlchemyError:
            print_exc()
            log_err('error: user with email `{}` does not exist'.format(email))
        else:
            success += 1
        if i % 100 == 0:
            log.info('\nUploaded {}/{} Scores\n'.format(i, total))
    db.session.commit()

    log.info('\nSuccessfully uploaded {} "{}" scores (with {} errors)'.format(success, kind, total - success))

    return '/admin/course/{cid}/assignments/{aid}/scores'.format(
                cid=jobs.get_current_job().course_id, aid=assign_id)

