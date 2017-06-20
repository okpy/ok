import math
import io
import csv
from collections import defaultdict
from datetime import datetime as dt

from server import jobs
from server.models import Assignment, ExternalFile
from server.utils import encode_id, local_time, output_csv_iterable
from server.constants import TIMESCALES

timescales = {'days':86400, 'hours':3600, 'minutes':60}

def timediff(created, deadline, timescale):
    secs_over = (created - deadline).total_seconds()
    return math.ceil(secs_over / timescales[timescale.lower()])


def save_csv(csv_name, header, rows, show_results, user, course, logger):
    logger.info('Outputting csv...\n')
    csv_iterable = output_csv_iterable(header, rows)

    logger.info('Uploading...')
    upload = ExternalFile.upload(csv_iterable, 
                user_id=user.id, course_id=course.id, name=csv_name, 
                prefix='jobs/slips/{}'.format(course.offering))
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

    course_slips = defaultdict(list)
    for i, assign in enumerate(assigns, 1):
        logger.info('Processing {} ({} of {})...'
            .format(assign.display_name, i, len(assigns_set)))
        subms = assign.course_submissions(include_empty=False)
        deadline = assign.due_date
        assign_slips = {}
        for subm in subms:
            email = subm['user']['email']
            created = subm['backup']['created']
            slips = max(0, timediff(created, deadline, timescale))
            assign_slips[email] = [(assign.display_name, slips)]
        course_slips = {k:course_slips[k] + assign_slips[k] 
                        for k in course_slips.keys() | assign_slips.keys()}

    def get_row(email, assign_slips):
        total_slips = sum((s for a, s in assign_slips))
        assignments = ', '.join([a for a, s in assign_slips if s > 0])
        return (email, total_slips, assignments)
    
    header = (
        'User Email', 
        'Slip {} Used'.format(timescale.title()),
        'Late Assignments')
    rows = (get_row(*user_slips) for user_slips in course_slips.items())
    created_time = local_time(dt.now(), course, fmt='%m-%d-%I-%M-%p')
    csv_name = '{}_{}.csv'.format(course.offering.replace('/', '-'), created_time)

    return save_csv(csv_name, header, rows, show_results, user, course, logger)


@jobs.background_job
def calculate_assign_slips(assign_id, timescale, show_results):
    logger = jobs.get_job_logger()
    logger.info('Calculating Slip {}...'.format(timescale.title()))
    
    user = jobs.get_current_job().user
    assignment = Assignment.query.get(assign_id)
    course = assignment.course
    subms = assignment.course_submissions(include_empty=False)
    deadline = assignment.due_date

    def get_row(subm):
        email = subm['user']['email']
        created = subm['backup']['created']
        slips = max(0, timediff(created, deadline, timescale))
        return (email, slips)

    header = (
        'User Email', 
        'Slip {} Used'.format(timescale.title()))
    rows = (get_row(subm) for subm in subms)
    created_time = local_time(dt.now(), course, fmt='%m-%d-%I-%M-%p')
    csv_name = '{}_{}.csv'.format(assignment.name.replace('/', '-'), created_time)

    return save_csv(csv_name, header, rows, show_results, user, course, logger)