import time

from server import jobs

@jobs.background_job
def test_job(duration=0, should_fail=False):
    logger = jobs.get_job_logger()

    logger.info('Starting...')
    time.sleep(duration)
    if should_fail:
        1/0
    logger.info('Finished!')
    return "Waited for <b>{}</b> seconds!".format(duration)
