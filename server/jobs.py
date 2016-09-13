import functools
import io
import logging
import time

from flask_login import current_user
from flask_rq import get_connection, get_queue
import redis.exceptions
import rq

from server.models import db, Job

def get_job_id():
    rq_job = rq.get_current_job(connection=get_connection())
    return rq_job.id

def get_job_logger():
    return logging.getLogger('{}.job_{}'.format(__name__, get_job_id()))

def background_job(f):
    @functools.wraps(f)
    def job_handler(*args, **kwargs):
        job = Job.query.get(get_job_id())
        job.status = 'running'
        db.session.commit()

        stream = io.StringIO()
        logger = get_job_logger()
        logger.setLevel(logging.INFO)
        logger.addHandler(logging.StreamHandler(stream))

        try:
            f(*args, **kwargs)
        except:
            job.failed = True
            logger.exception('Job failed')

        job.status = 'finished'
        job.log = stream.getvalue()
        stream.close()
        db.session.commit()

    return job_handler

def enqueue_job(func, *args, **kwargs):
    job = Job(
        status='queued',
        user_id=current_user.id,
        name=func.__name__,
    )
    db.session.add(job)
    db.session.commit()

    try:
        get_queue().enqueue_call(
            func=func,
            args=args,
            kwargs=kwargs,
            job_id=str(job.id),
        )
    except redis.exceptions.ConnectionError as e:
        job.failed = True
        job.status = 'finished'
        job.log = 'Could not connect to Redis: ' + str(e)
        db.session.add(job)
        db.session.commit()

    return job

@background_job
def test_job(duration=0, should_fail=False):
    logger = get_job_logger()

    logger.info('Starting...')
    time.sleep(duration)
    if should_fail:
        1/0
    logger.info('Finished!')
