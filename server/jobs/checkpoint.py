from sqlalchemy import or_
from collections import defaultdict

from server import jobs
from server.models import Assignment, Score, Backup, db
from server.utils import server_time_obj
from server.autograder import autograde_backups

@jobs.background_job
def assign_scores(assign_id, score, kind, message, deadline,
                     include_backups=True, grade_backups=False):
    logger = jobs.get_job_logger()
    current_user = jobs.get_current_job().user

    assignment = Assignment.query.get(assign_id)
    students = [e.user_id for e in assignment.course.get_students()]
    submission_time = server_time_obj(deadline, assignment.course)

    # Find all submissions (or backups) before the deadline
    backups = Backup.query.filter(
        Backup.assignment_id == assign_id,
        or_(Backup.created <= deadline, Backup.custom_submission_time <= deadline)
    ).order_by(Backup.created.desc()).group_by(Backup.submitter_id)

    if not include_backups:
        backups = backups.filter(Backup.submit == True)

    all_backups =  backups.all()

    if not all_backups:
        logger.info("No submissions were found with a deadline of {}."
                    .format(deadline))
        return "No Scores Created"

    score_counter, seen = 0, set()

    unique_backups = []

    for back in all_backups:
        if back.creator not in seen:
            unique_backups.append(back)
            seen |= back.owners()

    total_count = len(unique_backups)
    logger.info("Found {} unique and eligible submissions...".format(total_count))

    if grade_backups:
        logger.info('\nAutograding {} backups'.format(total_count))
        backup_ids = [back.id for back in unique_backups]
        try:
            autograde_backups(assignment, current_user.id, backup_ids, logger)
        except ValueError:
            logger.info('Could not autograde backups - Please add an autograding key.')
    else:
        for back in unique_backups:
            new_score = Score(score=score, kind=kind, message=message,
                              user_id=back.submitter_id,
                              assignment=assignment, backup=back,
                              grader=current_user)

            db.session.add(new_score)
            new_score.archive_duplicates()

            score_counter += 1
            if score_counter % 100 == 0:
                logger.info("Scored {} of {}".format(score_counter, total_count))

        # only commit if all scores were successfully added
        db.session.commit()

    logger.info("Left {} '{}' scores of {}".format(score_counter, kind.title(), score))
    return '/admin/course/{cid}/assignments/{aid}/scores'.format(
                cid=jobs.get_current_job().course_id, aid=assignment.id)







