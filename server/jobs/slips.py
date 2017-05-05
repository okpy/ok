from datetime import datetime as dt
import math
import io
import csv

from server import jobs
from server.models import Assignment, ExternalFile
from server.utils import encode_id, local_time, output_csv_iterable
from server.constants import TIMESCALES

timescales = {'days':86400, 'hours':3600, 'minutes':60}

def timediff(created, deadline, timescale):
    secs_over = (created - deadline).total_seconds()
    return math.ceil(secs_over / timescales[timescale.lower()])

@jobs.background_job
def calculate_course_slips(assigns, timescale, show_results):
    logger = jobs.get_job_logger()
    logger.info(assigns)
    logger.info(timescale)
    logger.info(show_results)

@jobs.background_job
def calculate_assign_slips(assign_id, timescale, show_results):
    logger = jobs.get_job_logger()
    job = jobs.get_current_job()

    logger.info('Calculating Slip {}...'.format(timescale.title()))

    assignment = Assignment.query.get(assign_id)
    course = assignment.course
    subms = assignment.course_submissions(include_empty=False)
    deadline = assignment.due_date

    def get_row(subm):
        email = subm['user']['email']
        created = subm['backup']['created']
        slips = min(0, timediff(created, deadline, timescale))
        return [email, slips]

    header = ('User Email', 'Slip {} Used'.format(timescale.title()))
    rows = (get_row(subm) for subm in subms)
    logger.info('Outputting csv...\n')
    csv_iterable = output_csv_iterable(header, rows)

    logger.info('Uploading...')
    created_time = local_time(dt.now(), course, fmt='%m-%d-%I-%M-%p')
    csv_name = '{}_{}.csv'.format(assignment.name.replace('/', '-'), created_time)
    upload = ExternalFile.upload(csv_iterable, 
                user_id=job.user.id, course_id=course.id, name=csv_name, 
                prefix='jobs/slips/{}'.format(course.offering))
    logger.info('Saved as: {}'.format(upload.object_name))

    download_link = "/files/{}".format(encode_id(upload.id))
    logger.info('Download link: {} (see "result" above)\n'.format(download_link))

    if show_results:
        logger.info('Results:\n')
        csv_data = ''.join([row.decode('utf-8') for row in csv_iterable])
        logger.info(csv_data)

    return download_link


