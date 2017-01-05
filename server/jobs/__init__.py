import functools
import io
import logging

from flask_login import current_user
from flask_rq import get_connection, get_queue
import redis.exceptions
import rq

from server.models import db, Job

class JobLogHandler(logging.StreamHandler):
    """Stream log contents to buffer and to DB. """
    def __init__(self, stream, job, log_every=10):
        super().__init__(stream)
        self.stream = stream
        self.job = job
        self.counter = 0
        self.log_every = log_every

    def handle(self, record):
        self.counter += 1
        super().handle(record)
        print(record.message)
        if (self.counter % self.log_every) == 0:
            self.job.log = self.contents
            db.session.commit()

    @property
    def contents(self):
        return self.stream.getvalue()

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
        handler = JobLogHandler(stream, job)
        logger = get_job_logger()

        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        return_value = None

        try:
            return_value = f(*args, **kwargs)
        except:
            job.failed = True
            logger.exception('Job failed')

        job.status = 'finished'
        job.result = return_value
        job.log = handler.contents
        stream.close()
        db.session.commit()

    return job_handler

def enqueue_job(func, *args,
                description=None, course_id=None, user_id=None, timeout=300,
                result_kind='string', **kwargs):
    if not description:
        raise ValueError('Description required to start background job')
    if not course_id:
        raise ValueError('Course ID required to start background job')
    if not user_id:
        user_id = current_user.id
    job = Job(
        status='queued',
        course_id=course_id,
        user_id=user_id,
        name=func.__name__,
        description=description,
        result_kind=result_kind
    )
    db.session.add(job)
    db.session.commit()

    try:
        get_queue().enqueue_call(
            func=func,
            args=args,
            kwargs=kwargs,
            job_id=str(job.id),
            timeout=timeout
        )
    except redis.exceptions.ConnectionError as e:
        job.failed = True
        job.status = 'finished'
        job.log = 'Could not connect to Redis: ' + str(e)
        db.session.add(job)
        db.session.commit()

    return job
