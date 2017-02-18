import os
from collections import defaultdict

import server

from server import jobs
from server.constants import STUDENT_ROLE
from server.models import Assignment, Enrollment, User, Score, db
from server.utils import send_email

@jobs.background_job
def email_scores(assignment_id, score_tags, subject, body,
                 reply_to=None, dry_run=False):
    log = jobs.get_job_logger()
    job_creator = jobs.get_current_job().user

    assign = Assignment.query.get(assignment_id)

    students = [e.user for e in (Enrollment.query
                        .options(db.joinedload('user'))
                        .filter(Enrollment.role == STUDENT_ROLE,
                                Enrollment.course == assign.course)
                        .all())]

    for kind in score_tags:
        if kind not in assign.published_scores:
            log.warning(("{0} scores are not visible to students. "
                         " Please publish them and try again").format(kind))
            return "Not sent - {} is not published".format(kind)

    email_counter = 0
    seen_ids = set()
    for student in students:
        if student.id in seen_ids:
            continue
        user_ids = assign.active_user_ids(student.id)
        seen_ids |= user_ids
        scores = [s for s in assign.scores(user_ids) if s.kind in score_tags]
        if scores:
            users = User.query.filter(User.id.in_(user_ids))
            primary, cc = users[0].email, [u.email for u in users[1:]]
            if dry_run:
                primary, cc = job_creator.email, []

            result = send_email(primary,
                subject, body,
                cc=cc,
                template='email/scores.html',
                title=subject,
                from_name=assign.course.display_name,
                scores=scores,
                reply_to=reply_to,
                link_text="View on okpy.org",
                link="https://okpy.org/" + assign.name, # Don't have url_for
                assignment=assign.display_name)

            if result:
                log.info("Sent to {}".format(', '.join([primary] + cc)))
                email_counter += 1

        # Send a few emails in dry run mode.
        if dry_run and email_counter >= 2:
            message = "Run with dry run mode"
            log.info(message)
            return message

    message = "Sent {} emails".format(email_counter)
    log.info(message)
    return message



