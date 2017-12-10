import os
from collections import defaultdict

import server

from server import jobs
from server.constants import STUDENT_ROLE
from server.models import Assignment, Enrollment, Backup, User, Score, db
from server.utils import send_email

@jobs.background_job
def score_from_csv(assign_id, email_label=None, score_label=None, uploaded_csv=None, kind='total'):
    log = jobs.get_job_logger()
    current_user = jobs.get_current_job().user

    if not uploaded_csv:
        rows = csv.reader(form.csv.data.splitlines())
    else:
        rows = uploaded_csv

    cid = jobs.get_current_job().course_id
    assign = Assignment.query.filter_by(id=assign_id, course_id=cid).one_or_none()

    line_num = 0
    for i, entry in enumerate(rows, start=1):
        try:
            if uploaded_csv and email_label and score_label:
                email, score = entry[email_label], entry[score_label]
            else:
                entry = [x.strip() for x in entry]
                email, score = entry[0], entry[1]
        except Exception as e:
            log.info('csv not formatted properly on line {linenum}: {entry}'.format(linenum=line_num,entry=entry))
            continue

        if not score:
            score = 0

        user = User.query.filter_by(email=email).one_or_none()

        try:
            backup = Backup.create(
                submitter=user,
                assignment_id=assign.id,
                submit=True
            )
        except Exception as e:
            print(e)
            log.info('User with email `{}` not Found.'.format(email))
            continue

        uploaded_score = Score(grader_id=current_user.id, assignment=backup.assignment,\
                    backup=backup, user_id=backup.submitter_id, score=score, kind=kind)

        if i % 100 == 0:
            log.info('Uploaded {}/{} Scores'.format(i, len(rows)))

        db.session.add(uploaded_score)
        #CURRENTLY NOT ARCHIVING OLD SCORES
        uploaded_score.archive_duplicates()
        line_num += 1

    db.session.commit()

    return '/admin/course/{cid}/assignments/{aid}/scores'.format(cid=cid, aid=assign_id)
