

from server import jobs

@jobs.background_job
def calculate_slips():
    logger = jobs.get_job_logger()
    logger.info('hello world!')
