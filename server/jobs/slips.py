from datetime import datetime as dt
import math
import io
import csv

from server import jobs
from server.models import Assignment
from server.constants import TIMESCALES

timescales = {'days':86400, 'hours':3600, 'minutes':60}

def timediff(created, deadline, timescale):
    secs_over = (created - deadline).total_seconds()
    return math.ceil(secs_over / timescales[timescale.lower()])

def csv_data(header, rows):
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
    writer.writerow(header)
    [writer.writerow(row) for row in rows]
    return output.getvalue()

@jobs.background_job
def calculate_slips(assign_id, timescale):
    logger = jobs.get_job_logger()
    job = jobs.get_current_job()

    logger.info('Calculating Slip {}...'.format(timescale.title()))

    assignment = Assignment.query.get(assign_id)
    subms = assignment.course_submissions(include_empty=False)
    deadline = assignment.due_date

    def get_row(subm):
        email = subm['user']['email']
        created = subm['backup']['created']
        slips = min(0, timediff(created, deadline, timescale))
        return [email, slips]

    header = ('User Email', 'Slip {} Used'.format(timescale.title()))
    rows = (get_row(subm) for subm in subms)
    data = csv_data(header, rows)

    logger.info(repr(data))
    
    # upload = ExternalFile.upload(csv_data, user_id=1, course_id=1,
    #     name='temp.okfile', prefix='jobs/example/')



