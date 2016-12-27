import collections

import requests.exceptions

from server import constants, jobs
from server.canvas import api
from server.models import CanvasAssignment, Enrollment
from server.utils import encode_id

@jobs.background_job
def upload_scores(canvas_assignment_id):
    logger = jobs.get_job_logger()
    canvas_assignment = CanvasAssignment.query.get(canvas_assignment_id)
    canvas_course = canvas_assignment.canvas_course
    assignment = canvas_assignment.assignment
    course = assignment.course

    logger.info('Starting bCourses upload')
    logger.info('bCourses assignment URL: {}'.format(canvas_assignment.url))
    logger.info('OK assignment: {}'.format(assignment.display_name))
    logger.info('Scores: {}'.format(', '.join(canvas_assignment.score_kinds)))

    students = api.get_students(canvas_course)
    old_scores = api.get_scores(canvas_assignment)
    new_scores = {}
    stats = collections.Counter()

    row_format = '{!s:>10}  {!s:<55}  {!s:<6}  {!s:>9}  {!s:>9}'
    logger.info(row_format.format('STUDENT ID', 'EMAIL', 'BACKUP', 'OLD SCORE', 'NEW SCORE'))

    for student in students:
        canvas_user_id = student['id']
        sid = student['sis_user_id']
        enrollments = Enrollment.query.filter_by(
            course_id=canvas_course.course_id,
            sid=sid,
            role=constants.STUDENT_ROLE,
        ).all()
        emails = ','.join(enrollment.user.email for enrollment in enrollments) or 'None'
        scores = []
        for enrollment in enrollments:
            user_ids = assignment.active_user_ids(enrollment.user_id)
            scores.extend(assignment.scores(user_ids))
        scores = [s for s in scores if s.kind in canvas_assignment.score_kinds]
        old_score = old_scores.get(canvas_user_id)
        if not scores:
            new_score = None
            backup_id = None
            stats['no_scores'] += 1
        else:
            max_score = max(scores, key=lambda score: score.score)
            new_score = max_score.score
            backup_id = encode_id(max_score.backup_id)
            if old_score != new_score:
                new_scores[canvas_user_id] = new_score
                stats['updated'] += 1
            else:
                stats['not_changed'] += 1
        logger.info(row_format.format(sid, emails, backup_id, old_score, new_score))

    if new_scores:
        api.put_scores(canvas_assignment, new_scores)

    stats = ('{updated} updated, {not_changed} not changed, '
             '{no_scores} no scores'.format(**stats))
    logger.info(stats)
    return stats
