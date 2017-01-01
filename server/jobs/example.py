import time
import io

from server import jobs
from server.models import ExternalFile
from server.utils import encode_id

@jobs.background_job
def test_job(duration=0, should_fail=False, make_file=False):
    logger = jobs.get_job_logger()

    logger.info('Starting...')
    time.sleep(duration)
    if should_fail:
        1/0
    if make_file:
        data = io.BytesIO(b'print("Hello World")\n'*duration)
        upload = ExternalFile.upload(data, user_id=1, course_id=1,
                                     name='temp.py', prefix='jobs/example/')
        logger.info("Saved as: {}".format(upload.object_name))
        logger.info('File ID: {0}'.format(encode_id(upload.id)))
        msg = ("Waited for <a href='/files/{0}'> {1} seconds </a>"
               .format(encode_id(upload.id), duration))
    else:
        msg = "Waited for <b>{}</b> seconds!".format(duration)
    logger.info('Finished!')
    return msg
