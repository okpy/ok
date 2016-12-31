import time
import tempfile

from server import jobs
from server.models import ExternalFile, db
from server.utils import upload_file, encode_id

@jobs.background_job
def test_job(duration=0, should_fail=False, make_file=False):
    logger = jobs.get_job_logger()

    logger.info('Starting...')
    time.sleep(duration)
    if should_fail:
        1/0
    if make_file:
        with tempfile.NamedTemporaryFile() as tf:
            for _ in range(duration):
                tf.write('Hello world!\n'.encode('utf-8'))
            tf.flush()
            upload = upload_file(tf.name, name='temp.txt', prefix='jobs/example/')
            container = upload.container.name or upload.container.driver.key
            logger.info("Container: {}. Saved as: {}".format(container, upload.name))
            file = ExternalFile(
                container=container,
                filename='temp.txt',
                object_name=upload.name,
                course_id=1,
                user_id=1,
                is_staff=True)
            db.session.add(file)
            db.session.commit()
            logger.info('File: /files/{0}'.format(encode_id(file.id)))

    logger.info('Finished!')
    return "Waited for <b>{}</b> seconds!".format(duration)
