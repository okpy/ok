import math
import io
import csv
from collections import defaultdict
from datetime import datetime as dt

from server import jobs
from server.models import Assignment, ExternalFile, User
from server.utils import encode_id, local_time, generate_csv
from server.constants import TIMESCALES

"""
 TODO: 
 - Support for timezone in filename?
"""


timescales = {'days': 86400, 'hours': 3600, 'minutes': 60}


def timediff(created, deadline, timescale):
    secs_over = (created - deadline).total_seconds()
    return math.ceil(secs_over / timescales[timescale.lower()])


def save_csv(csv_name, header, rows, show_results, user, course, logger):
    logger.info('Outputting csv...\n')

    def selector_fn(lst):
        if len(lst) != len(header):
            raise IndexError
        result = {}
        for i in range(len(lst)):
            result[header[i]] = lst[i]
        return [result]

    csv_iterable = list(map(lambda x: bytes(x, 'utf-8'), generate_csv(rows, header, selector_fn)))

    logger.info('Uploading...')
    upload = ExternalFile.upload(csv_iterable, 
                user_id=user.id, course_id=course.id, name=csv_name, 
                prefix='slips_')
    logger.info('Saved as: {}'.format(upload.object_name))

    download_link = "/files/{}".format(encode_id(upload.id))
    logger.info('Download link: {} (see "result" above)\n'.format(download_link))

    if show_results:
        logger.info('Results:\n')
        csv_data = ''.join([row.decode('utf-8') for row in csv_iterable])
        logger.info(csv_data)

    return download_link


@jobs.background_job
def calculate_course_slips(assigns, timescale, show_results):
    logger = jobs.get_job_logger()
    logger.info('Calculating Slip {}...\n'.format(timescale.title()))

    job = jobs.get_current_job()
    user = job.user
    course = job.course
    assigns_set = set(assigns)
    assigns = (a for a in course.assignments if a.id in assigns_set)
    rows = []

    for i, assign in enumerate(assigns, 1):
        logger.info('Processing {} ({} of {})...'
                    .format(assign.display_name, i, len(assigns_set)))
        students_ids = get_students_with_submission(assign)
        subms = []
        for id in students_ids:
            subm = assign.final_submission([id])
            if subm:
                subms.append(subm)
        deadline = assign.due_date
        for subm in subms:
            curr_user = subm.submitter
            enrollment = curr_user.enrollments()[0]
            sid = enrollment.sid
            email = curr_user.email
            created = subm.submission_time
            slips = max(0, timediff(created, deadline, timescale))
            if slips > 0:
                rows.append([assign.display_name, sid, email, slips])

    header = [
        'Assignment',
        'User SID',
        'User Email',
        'Slip {} Used'.format(timescale.title())]
    created_time = local_time(dt.now(), course, fmt='%m-%d_%I-%M-%p')
    csv_name = '{}_{}.csv'.format(course.display_name.replace('/', '-'), created_time)

    return save_csv(csv_name, header, rows, show_results, user, course, logger)


def get_students_with_submission(assignment):
    """Get a list of IDs of students who have made a submission
    for the current assignment.

    :param ASSIGNMENT instance of the model Assignment

    This code is copied from the assignment_stats() method
    in the Assignment model methods. May need refactoring."""

    data = assignment.course_submissions()
    students_ids = set(s['user']['id'] for s in data if s['backup'] and s['backup']['submit'])
    return students_ids


@jobs.background_job
def calculate_assign_slips(assign_id, timescale, show_results):
    logger = jobs.get_job_logger()
    logger.info('Calculating Slip {}...'.format(timescale.title()))
    
    user = jobs.get_current_job().user
    assignment = Assignment.query.get(assign_id)
    course = assignment.course
    students_ids = get_students_with_submission(assignment)
    subms = []
    for id in students_ids:
        subm = assignment.final_submission([id])
        if subm:
            subms.append(subm)
    deadline = assignment.due_date
    rows = []
    for subm in subms:
        curr_user = subm.submitter
        enrollment = curr_user.enrollments()[0]
        sid = enrollment.sid
        email = curr_user.email
        created = subm.submission_time
        slips = max(0, timediff(created, deadline, timescale))
        if slips > 0:
            rows.append([sid, email, slips])

    header = [
        'User SID',
        'User Email', 
        'Slip {} Used'.format(timescale.title())]
    created_time = local_time(dt.now(), course, fmt='%m-%d_%I-%M-%p')
    csv_name = '{}_{}.csv'.format(assignment.display_name.replace('/', '-'), created_time)

    return save_csv(csv_name, header, rows, show_results, user, course, logger)