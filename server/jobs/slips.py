

from server import jobs
from server.models import Assignment
from server.constants import TIMESCALES
from datetime import datetime as dt
from math import ceil

timescales = {'days':86400, 'hours':3600, 'minutes':60}

def timediff(created, deadline, timescale):
    secs_over = (created - deadline).total_seconds()
    return ceil(secs_over / timescales[timescale.lower()])

@jobs.background_job
def calculate_slips(assign_id, timescale):
    logger = jobs.get_job_logger()
    job = jobs.get_current_job()
    
    logger.info('Calculating slip {}...'.format(timescale))
    assignment = Assignment.query.get(assign_id)
    subms = assignment.course_submissions(include_empty=False)
    deadline = assignment.due_date
    for subm in subms:
        email = subm['user']['email']
        created = subm['backup']['created']
        logger.info('{} {}'
            .format(email, timediff(created, deadline, timescale)))

