#!/usr/bin/env python
# encoding: utf-8
"""
tests.py

TODO: These tests need to be updated to support the Python 2.7 runtime

"""
import os
import unittest

from google.appengine.ext import testbed

from app import app


class SimpleTestCase(unittest.TestCase):

    def setUp(self):
        # Flask apps testing. See: http://flask.pocoo.org/docs/testing/
        app.config['TESTING'] = True
        app.config['CSRF_ENABLED'] = False
        self.app = app.test_client()
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()

    def tearDown(self):
        self.testbed.deactivate()

    def setCurrentUser(self, email, user_id, is_admin=False):
        os.environ['USER_EMAIL'] = email or ''
        os.environ['USER_ID'] = user_id or ''
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'

    def test_home_works(self):
        rv = self.app.get('/')
        assert rv.status == '200 OK', "Wrong status: %s" % rv.status

if __name__ == '__main__':
    unittest.main()
