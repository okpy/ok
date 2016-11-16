import requests.exceptions

from server import jobs
from server.canvas import api
from server.models import CanvasAssignment

@jobs.background_job
def upload_assignment_scores(canvas_assignment_id):
    logger = jobs.get_job_logger()
    canvas_assignment = CanvasAssignment.query.get(canvas_assignment_id)
    assignment = canvas_assignment.assignment

    logger.info('Starting bCourses upload')
    logger.info('bCourses assignment URL: {}'.format(canvas_assignment.url))
    logger.info('OK assignment: {}'.format(assignment.display_name))
    logger.info('Scores: {}'.format(', '.join(canvas_assignment.score_kinds)))
