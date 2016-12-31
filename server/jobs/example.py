import time
import tempfile

from server import jobs
from server.models import ExternalFile, db
from server.utils import upload_file

@jobs.background_job
def test_job(duration=0, should_fail=False, should_write=False):
    logger = jobs.get_job_logger()

    logger.info('Starting...')
    time.sleep(duration)
    if should_fail:
        1/0
    if duration >= 5:  # Arbitrary limit
        with tempfile.NamedTemporaryFile() as tf:
            for _ in range(duration):
                tf.write('Hello world!\n'.encode('utf-8'))
            tf.flush()
            upload = upload_file(tf.name)
            file = ExternalFile(
                container=upload.container.driver.key,
                filename='temp.txt',
                object_name=upload.name,
                course_id=1,
                user_id=1,
                is_staff=True)
            db.session.add(file)
            db.session.commit()
            logger.info('File: /files/{0}'.format(file.id))

    logger.info('Finished!')
    return "Waited for <b>{}</b> seconds!".format(duration)
