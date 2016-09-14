import re

from flask_rq import get_worker

from server import jobs
from server.models import db, Job
from tests import OkTestCase

class TestJob(OkTestCase):
    def setUp(self):
        super(TestJob, self).setUp()
        self.setup_course()

    def run_jobs(self):
        get_worker().work(burst=True)
        db.session.expire_all()

    def test_dashboard_access(self):
        response = self.client.get('/rq/')
        self.assertRedirects(response, '/login/')

        self.login(self.staff1.email)
        response = self.client.get('/rq/')
        self.assert_403(response)

        self.login(self.admin.email)
        response = self.client.get('/rq/')
        self.assert_200(response)

    def start_test_job(self, should_fail=False):
        self.login(self.admin.email)
        url = '/admin/course/{}/jobs/test/'.format(self.course.id)
        response = self.client.post(url, data={
            'duration': 0,
            'should_fail': 'checked' if should_fail else '',
        }, follow_redirects=True)
        self.assert_200(response)

        # Get the job ID with a regex. Yeah, I know
        match = re.search(r'Job\s+(\d+)', response.data.decode('utf-8'))
        job_id = match.group(1)
        job = Job.query.get(job_id)

        self.assertEqual(job.user_id, self.admin.id)
        self.assertEqual(job.name, 'test_job')
        self.assertEqual(job.status, 'queued')
        self.assertFalse(job.failed)
        self.assertEqual(job.log, None)

        return job_id

    def test_job(self):
        job_id = self.start_test_job(should_fail=False)
        self.run_jobs()
        job = Job.query.get(job_id)
        self.assertEqual(job.status, 'finished')
        self.assertFalse(job.failed)
        self.assertEqual(job.log, 'Starting...\nFinished!\n')

    def test_failing_job(self):
        job_id = self.start_test_job(should_fail=True)
        self.run_jobs()
        job = Job.query.get(job_id)
        self.assertEqual(job.status, 'finished')
        self.assertTrue(job.failed)
        self.assertIn('Starting...', job.log)
        self.assertIn('Job failed', job.log)
        self.assertIn('Traceback', job.log)
        self.assertIn('ZeroDivisionError', job.log)
