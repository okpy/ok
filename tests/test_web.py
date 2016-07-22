import json

import requests
from flask_testing import LiveServerTestCase
from selenium import webdriver

from server import create_app
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

        def create_app(self):
            app = create_app('settings/test.py')
            app.config['TESTING'] = True
            app.config['DEBUG'] = False
            # Default port is 5000
            # app.config['LIVESERVER_PORT'] = 8943
            return app

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

        def login(self, role="admin"):
            self.driver.get(self.get_server_url() + "/testing-login/")
            # self.driver.get_screenshot_as_file('login.png')
            self.assertIn('Login', self.driver.title)

            self.driver.find_element_by_id(role).click()
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

        def test_phantom_web(self):
            self.pageLoad(self.get_server_url())
            self.assertIn('Ok', self.driver.title)
            self.driver.find_element_by_id('testing-login').click()
            self.assertIn('Login', self.driver.title)

            self.driver.find_element_by_tag_name('button').click()
            self.assertIn('Courses | Ok', self.driver.title)
            self.pageLoad(self.get_server_url())
            self.assertIn('Courses | Ok', self.driver.title)

            self.driver.find_element_by_id('logout').click()
            self.assertIn('Ok |', self.driver.title)

        def test_login_admin_reject(self):
            self.login(role="student")
            self.pageLoad(self.get_server_url() + "/admin/")
            self.assertTrue("not on the course staff" in self.driver.page_source)
            self.assertIn('Courses | Ok', self.driver.title)

        def test_assignment_info(self):
            self.login(role="admin")
            self.pageLoad(self.get_server_url() + "/admin/course/1/assignments/1")
            self.assertIn('Ok -', self.driver.title)
            self.assertTrue("Hog" in self.driver.page_source)

            self.pageLoad(self.get_server_url() + "/admin/course/1/assignments/1/stats")
            self.assertIn('Ok -', self.driver.title)
            self.assertTrue("Hog Stats" in self.driver.page_source)

        def test_queue_create(self):
            self.login(role="admin")
            self.pageLoad(self.get_server_url() + "/admin/")
            # if needed for debug: self.driver.get_screenshot_as_file('staff.png')

            self.pageLoad(self.get_server_url() + "/admin/course/1/assignments/1/queues/new")
            self.driver.find_element_by_css_selector('form button.btn-default').click()
            self.assertTrue("Hog" in self.driver.page_source)
            # Ensure tasks were created for two staff members
            self.assertTrue("for 2 staff" in self.driver.page_source)
