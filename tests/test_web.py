import json

import requests
from flask_testing import LiveServerTestCase
from selenium import webdriver

from server import create_app
from tests import OkTestCase

class WebTest(LiveServerTestCase):

    def setUp(self):
        try:
            self.driver = webdriver.PhantomJS()
        except:
            print("PhantomJS is not installed. Not running integration tests")
            exit(0)
        OkTestCase.setUp(self)
        OkTestCase.setup_course(self)

    def create_app(self):
        app = create_app('settings/test.py')

        app.config['TESTING'] = True
        # Default port is 5000
        app.config['LIVESERVER_PORT'] = 8943
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
