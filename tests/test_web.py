""" Selenium driver for PhantomJS headless browser testing.
Development: self.driver.get_screenshot_as_file('snap.png')
Docs: http://selenium-python.readthedocs.io/getting-started.html
"""
import json
import os
import signal
import urllib.parse

import requests
from flask_testing import LiveServerTestCase
from selenium import webdriver

from server import create_app
from server import models

from tests import OkTestCase

try:
    driver = webdriver.PhantomJS()
except:
    print("PhantomJS is not installed. Not running integration tests")
    driver = None

if driver:
    driver.quit()

    class WebTest(LiveServerTestCase):

        def setUp(self):
            self.driver = webdriver.PhantomJS()
            OkTestCase.setUp(self)
            OkTestCase.setup_course(self)
            self.driver.set_window_size(1268, 1024)

        def _seed_course(self):
            self.active_user_ids = [self.user1.id, self.user3.id]
            # Setup some submissisions
            message_dict = {'file_contents': {'backup.py': '1'}, 'analytics': {}}
            for i in range(5):
                for user_id in self.active_user_ids:
                    submit = True if i % 2 else False
                    backup = models.Backup(submitter_id=user_id,
                        assignment=self.assignment, submit=submit)
                    messages = [models.Message(kind=k, backup=backup,
                        contents=m) for k, m in message_dict.items()]
                    models.db.session.add_all(messages)
                    models.db.session.add(backup)
            models.db.session.commit()

            # Setup some groups
            models.Group.invite(self.user1, self.user4, self.assignment)
            group = models.Group.lookup(self.user1, self.assignment)
            group.accept(self.user4)

            models.Group.invite(self.user2, self.user3, self.assignment)

            self.oauth_client = models.Client(
                name='Testing Client',
                client_id='test-client',
                client_secret='secret',
                redirect_uris=['http://example.com/'],
                is_confidential=False,
                description='Sample App for testing OAuth',
                default_scopes=['email'],
            )
            models.db.session.add(self.oauth_client)
            models.db.session.commit()

        def create_app(self):
            app = create_app('settings/test.py')
            # Default port is 5000
            app.config['LIVESERVER_PORT'] = 8943
            return app

        def _terminate_live_server(self):
            """ Properly handle termination for coverage reports.
            Works on *nix systems (aka not windows).
            https://github.com/jarus/flask-testing/issues/70 """
            # Handle Windows
            if os.name == "nt":
                print("Coverage may not properly be reported on Windows")
                return LiveServerTestCase._terminate_live_server(self)
            os.kill(self._process.pid, signal.SIGINT)
            self._process.join()

        def tearDown(self):
            OkTestCase.tearDown(self)
            super(WebTest, self).tearDown()
            self.driver.quit()

        def pageLoad(self, url):
            self.driver.get(url)

            # View all requests made by the page
            for entry in self.driver.get_log('har'):
                data = json.loads(entry['message'])
                requests = data['log']['entries']
                for req in requests:
                    if not req['response']['status']:
                        print(req)
                        raise AssertionError('Request by page did not complete')

            # Assert no console messages
            self.assertEqual([], self.driver.get_log('browser'))

        def _login(self, role="admin"):
            self.driver.get(self.get_server_url() + "/testing-login/")
            # self.driver.get_screenshot_as_file('login.png')
            self.assertIn('Login', self.driver.title)

            self.driver.find_element_by_id(role).click()
            self.assertIn('Courses | Ok', self.driver.title)

        def _login_as(self, email=None):
            self.driver.get(self.get_server_url() + "/testing-login/")
            self.assertIn('Login', self.driver.title)

            input_element = self.driver.find_element_by_id("email-login")
            input_element.send_keys(email)
            input_element.submit()

            self.assertIn('Courses | Ok', self.driver.title)

        def test_server_is_up_and_running(self):
            response = requests.get(self.get_server_url())
            self.assertEqual(response.status_code, 200)

        def test_api_is_up_and_running(self):
            api_url = "{}/api/v3/".format(self.get_server_url())
            response = requests.get(api_url)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data['message'], 'success')
            self.assertEqual(data['data']['version'], 'v3')

        def test_static_pages(self):
            about_url = "{}/about/privacy/".format(self.get_server_url())
            self.pageLoad(about_url)
            self.assertIn('Privacy Policy | Ok', self.driver.title)

        def test_phantom_web(self):
            self.pageLoad(self.get_server_url())
            self.assertEquals('Ok', self.driver.title)
            self.driver.find_element_by_id('testing-login').click()
            self.assertIn('Login', self.driver.title)

            self.driver.find_element_by_tag_name('button').click()
            self.assertIn('Courses | Ok', self.driver.title)
            self.pageLoad(self.get_server_url())
            self.assertIn('Courses | Ok', self.driver.title)

            self.driver.find_element_by_id('logout').click()
            self.assertEquals('Ok', self.driver.title)

        def test_student_view(self):
            self._seed_course()

            self._login_as(email=self.user4.email)

            self.pageLoad(self.get_server_url())
            self.assertIn('Courses | Ok', self.driver.title)

            self.pageLoad("{}/cal/cs61a/sp16/".format(self.get_server_url()))
            self.assertTrue("Current Assignments" in self.driver.page_source)

            self.pageLoad("{}/cal/cs61a/sp16/proj1/".format(self.get_server_url()))

            self.driver.find_element_by_class_name("view-code").click()
            self.assertTrue("backup.py" in self.driver.page_source)

            self.pageLoad("{}/cal/cs61a/sp16/proj1/backups/".format(self.get_server_url()))
            self.pageLoad("{}/cal/cs61a/sp16/proj1/submissions/".format(self.get_server_url()))

        def test_student_remove_member(self):
            self._seed_course()
            self._login_as(email=self.user4.email)
            self.pageLoad("{}/cal/cs61a/sp16/proj1/".format(self.get_server_url()))
            self.assertTrue("student1@aol.com" in self.driver.page_source)

            # .click will send a sweet alert warning
            self.driver.find_element_by_id("remove-member").click()
            self.assertTrue("Are you sure" in self.driver.page_source)

            self.driver.find_element_by_id("remove-member").submit()
            self.assertTrue("student1@aol.com" not in self.driver.page_source)
            self.assertTrue("No Submission" in self.driver.page_source)

        def test_student_invalid_hash(self):
            self._seed_course()
            self._login_as(email=self.user4.email)
            self.driver.get("{}/cal/cs61a/sp16/proj1/xyz".format(self.get_server_url()))
            self.assertIn('404', self.driver.title)

        def test_web_submit_disabled(self):
            self._seed_course()
            self._login_as(email=self.user4.email)
            self.pageLoad("{}/cal/cs61a/sp16/proj1/submit".format(self.get_server_url()))
            self.assertTrue("This assignment cannot be submitted online" in self.driver.page_source)

        def test_web_submit_no_file(self):
            self._seed_course()
            self.assignment.uploads_enabled = True
            self.assignment.upload_info = 'Upload all the files!'
            models.db.session.commit()

            self._login_as(email=self.user4.email)
            self.pageLoad("{}/cal/cs61a/sp16/proj1/".format(self.get_server_url()))

            # Test with no files
            self.driver.find_element_by_id('new-submission').click()
            self.assertTrue("New Submission" in self.driver.page_source)
            self.driver.find_element_by_class_name('submit-btn').click()
            self.assertTrue("This field is required" in self.driver.page_source)

        def test_web_submit(self):
            self._seed_course()
            self.assignment.uploads_enabled = True
            self.assignment.upload_info = 'Upload all the files!'
            models.db.session.commit()

            self._login_as(email=self.user4.email)
            self.pageLoad("{}/cal/cs61a/sp16/proj1/submit".format(self.get_server_url()))

            # Disable the multiple select, PhantomJS doesn't seem to support it
            # https://github.com/detro/ghostdriver/issues/282 , https://github.com/ariya/phantomjs/issues/14331
            self.driver.execute_script("document.getElementById('file-select').removeAttribute('multiple')")
            file_input = self.driver.find_element_by_id("file-select")
            file_input.send_keys(os.path.abspath(__file__))
            self.driver.find_element_by_class_name('submit-btn').click()
            self.assertTrue("Uploaded submission" in self.driver.page_source)


        def test_web_submit_wrong_template(self):
            self._seed_course()
            self.assignment.uploads_enabled = True
            self.assignment.files = {'fizz.py': 'sample template\nfile'}
            self.assignment.upload_info = 'Upload all the files!'
            models.db.session.commit()

            self._login_as(email=self.user4.email)
            self.pageLoad("{}/cal/cs61a/sp16/proj1/submit".format(self.get_server_url()))

            # Disable the multiple select, PhantomJS doesn't seem to support it
            # https://github.com/detro/ghostdriver/issues/282 , https://github.com/ariya/phantomjs/issues/14331
            self.driver.execute_script("document.getElementById('file-select').removeAttribute('multiple')")
            file_input = self.driver.find_element_by_id("file-select")
            file_input.send_keys(os.path.abspath(__file__))
            self.driver.find_element_by_class_name('submit-btn').click()
            # Template did not match
            self.assertTrue("Missing file" in self.driver.page_source)

        def test_web_submit_with_template(self):
            self._seed_course()
            self.assignment.uploads_enabled = True
            dir_path, file_name = os.path.split(os.path.abspath(__file__))
            self.assignment.files = {file_name: 'sample template\nfile'}
            models.db.session.commit()
            self._login_as(email=self.user4.email)

            self.pageLoad("{}/cal/cs61a/sp16/proj1/submit".format(self.get_server_url()))
            self.driver.execute_script("document.getElementById('file-select').removeAttribute('multiple')")
            file_input = self.driver.find_element_by_id("file-select")
            file_input.send_keys(os.path.abspath(__file__))
            self.driver.find_element_by_class_name('submit-btn').click()
            self.assertTrue("Uploaded submission" in self.driver.page_source)

        def test_login_admin_reject(self):
            self._login(role="student")
            self.pageLoad(self.get_server_url() + "/admin/")
            self.assertTrue("not on the course staff" in self.driver.page_source)
            self.assertIn('Courses | Ok', self.driver.title)

        def test_assignment_info(self):
            self._login(role="admin")
            self.pageLoad(self.get_server_url() + "/admin/course/1/assignments/1")
            self.assertIn('Ok -', self.driver.title)
            self.assertTrue("Hog" in self.driver.page_source)

            self.pageLoad(self.get_server_url() + "/admin/course/1/assignments/1/stats")
            self.assertIn('Ok -', self.driver.title)
            self.assertTrue("Hog Stats" in self.driver.page_source)

        def test_queue_create(self):
            self._login(role="admin")
            self.pageLoad(self.get_server_url() + "/admin/")
            # if needed for debug: self.driver.get_screenshot_as_file('staff.png')

            self.pageLoad(self.get_server_url() + "/admin/course/1/assignments/1/queues/new")
            self.driver.find_element_by_css_selector('form button.btn-default').click()
            self.assertTrue("Hog" in self.driver.page_source)
            # Ensure tasks were created for two staff members
            self.assertTrue("for 2 staff" in self.driver.page_source)

        def test_login_redirect(self):
            self._seed_course()

            target_url = '{}/admin/course/{}/assignments'.format(
                self.get_server_url(),
                self.course.id)
            login_url = '{}/testing-login/'.format(self.get_server_url())

            # Access page while not logged in - should redirect to login
            self.pageLoad(target_url)
            self.assertEquals(self.driver.current_url, login_url)

            # Login and redirect back to original page
            self.driver.find_element_by_id('admin').click()
            self.assertEquals(self.driver.current_url, target_url)

        def test_oauth(self):
            self._seed_course()

            # Login
            self._login_as(self.user1.email)

            # Start OAuth and click "Confirm"
            self.pageLoad('{}/oauth/authorize?{}'.format(
                self.get_server_url(),
                urllib.parse.urlencode({
                    'response_type': 'code',
                    'client_id': self.oauth_client.client_id,
                    'redirect_uri': self.oauth_client.redirect_uris[0],
                    'scope': 'email',
                }),
            ))
            self.assertIn(self.user1.email, self.driver.page_source)
            self.driver.find_element_by_id('confirm-button').click()

            # Get code from redirect URI
            redirect_uri, query_string = self.driver.current_url.split('?')
            query = dict(urllib.parse.parse_qsl(query_string))
            self.assertEquals(redirect_uri, self.oauth_client.redirect_uris[0])
            self.assertIn('code', query)

        def test_oauth_logged_out(self):
            self._seed_course()

            # Start OAuth - redirects to log in
            self.pageLoad('{}/oauth/authorize?{}'.format(
                self.get_server_url(),
                urllib.parse.urlencode({
                    'response_type': 'code',
                    'client_id': self.oauth_client.client_id,
                    'redirect_uri': self.oauth_client.redirect_uris[0],
                    'scope': 'email',
                }),
            ))
            login_url = '{}/testing-login/'.format(self.get_server_url())
            self.assertEquals(self.driver.current_url, login_url)

            # Login and redirect back to original page
            input_element = self.driver.find_element_by_id("email-login")
            input_element.send_keys(self.user1.email)
            input_element.submit()

            # Now confirm OAuth
            self.assertIn(self.user1.email, self.driver.page_source)
            self.driver.find_element_by_id('confirm-button').click()

            # Get code from redirect URI
            redirect_uri, query_string = self.driver.current_url.split('?')
            query = dict(urllib.parse.parse_qsl(query_string))
            self.assertEquals(redirect_uri, self.oauth_client.redirect_uris[0])
            self.assertIn('code', query)
