from sqlalchemy import or_
from collections import defaultdict

from server import jobs
from server.models import Assignment, Score, Backup, db
from server.utils import server_time_obj

@jobs.background_job
def assign_scores(assign_id, score, kind, message, deadline,
                     include_backups=True):
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

    total_count, all_backups = backups.count(),  backups.all()
    if not total_count:
        logger.info("No submissions were found with a deadline of {}."
                    .format(deadline))
        return "No Scores Created"
    score_counter, seen = 0, set()

    logger.info("Found {} eligible submissions...".format(total_count))

    for back in all_backups:
        if back.creator in seen:
            score_counter += 1
            continue
        new_score = Score(score=score, kind=kind, message=message,
                          user_id=back.submitter_id,
                          assignment=assignment, backup=back,
                          grader=current_user)
        db.session.add(new_score)
        new_score.archive_duplicates()
        db.session.commit()

        score_counter += 1
        if score_counter % 5 == 0:
            logger.info("Scored {} of {}".format(score_counter, total_count))
        seen |= back.owners()

    result = "Left {} '{}' scores of {}".format(score_counter, kind.title(), score)
    logger.info(result)
    return result