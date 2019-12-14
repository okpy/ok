import io
import csv
import datetime as dt

from server import jobs
from server.models import Course, Enrollment, ExternalFile, db
from server.utils import encode_id, local_time
from server.constants import STUDENT_ROLE

TOTAL_KINDS = 'effort total regrade'.split()
COMP_KINDS = 'composition revision'.split()

def score_grabber(scores, kinds):
    return [scores.pop(kind.lower(), 0) for kind in kinds]

def scores_checker(scores, kinds):
    return any(kind.lower() in scores for kind in kinds)

def score_policy(scores):
    if scores_checker(scores, TOTAL_KINDS):
        total_score = max(score_grabber(scores, TOTAL_KINDS))
        scores['total'] = total_score
    if scores_checker(scores, COMP_KINDS):
        composition_score = max(score_grabber(scores, COMP_KINDS))
        scores['composition'] = composition_score
    return scores


def get_score_types(assignment):
    types = []
    scores = [s.lower() for s in assignment.published_scores]
    if scores_checker(scores, TOTAL_KINDS):
        types.append('total')
    if scores_checker(scores, COMP_KINDS):
        types.append('composition')
    if scores_checker(scores, ['checkpoint 1']):
        types.append('checkpoint 1')
    if scores_checker(scores, ['checkpoint 2']):
        types.append('checkpoint 2')
    return types

def get_headers(assignments):
    headers = ['Email', 'SID']
    new_assignments = []
    for assignment in assignments:
        new_headers = ['{} ({})'.format(assignment.display_name, score_type.title()) for
                score_type in get_score_types(assignment)
        if new_headers:
            new_assignments.append(assignment)
            headers.extend(new_headers)
            headers.append('{} (Submitted At)'.format(assignment.display_name))
    return headers, new_assignments

def export_student_grades(student, assignments):
    student_row = [student.user.email, student.sid]
    for assign in assignments:
        status = assign.user_status(student.user)
        submission_time = status.subm_time
        scores = {s.kind.lower(): s.score for s in status.scores}
        scores = score_policy(scores)
        score_types = get_score_types(assign)
        for score_type in score_types:
            if score_type in scores:
                student_row.append(scores[score_type])
            else:
                student_row.append(0)
        if submission_time:
            student_row.append(submission_time)
        else:
            student_row.append('No Submission')
    return student_row


@jobs.background_job
def export_grades():
    logger = jobs.get_job_logger()
    current_user = jobs.get_current_job().user
    course = Course.query.get(jobs.get_current_job().course_id)
    assignments = course.assignments
    students = (Enrollment.query
      .options(db.joinedload('user'))
      .filter(Enrollment.role == STUDENT_ROLE, Enrollment.course == course)
      .all())

    headers, assignments = get_headers(assignments)
    logger.info("Using these headers:")
    for header in headers:
        logger.info('\t' + header)
    logger.info('')

    total_students = len(students)
    with io.StringIO() as f:
        writer = csv.writer(f)
        writer.writerow(headers) # write headers

        for i, student in enumerate(students, start=1):
            row = export_student_grades(student, assignments)
            writer.writerow(row)
            if i % 50 == 0:
                logger.info('Exported {}/{}'.format(i, total_students))
        f.seek(0)
        created_time = local_time(dt.datetime.now(), course, fmt='%b-%-d %Y at %I-%M%p')
        csv_filename = '{course_name} Grades ({date}).csv'.format(
                course_name=course.display_name, date=created_time)
        # convert to bytes for csv upload
        csv_bytes = io.BytesIO(bytearray(f.read(), 'utf-8'))
        upload = ExternalFile.upload(csv_bytes, user_id=current_user.id, name=csv_filename,
                         course_id=course.id,
                         prefix='jobs/exports/{}/'.format(course.offering))

    logger.info('\nDone!\n')
    logger.info("Saved as: {0}".format(upload.object_name))
    return "/files/{0}".format(encode_id(upload.id))
