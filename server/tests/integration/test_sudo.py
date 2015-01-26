#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

import os
os.environ['FLASK_CONF'] = 'TEST'
import datetime
import urllib
import flask

from test_base import APIBaseTestCase, unittest #pylint: disable=relative-import

from app import models, utils

from google.appengine.ext import ndb

from app import auth
from app.authenticator import Authenticator, AuthenticationException

class SudoUnitTest(APIBaseTestCase):
    def get_accounts(self):
        """
        Returns the accounts you want to exist in your system.
        """
        return {
            "student0": models.User(
                email=["dummy@student.com"]
            ),
            "student1": models.User(
                email=["other@student.com"]
            ),
            "staff": models.User(
                email=["dummy@staff.com"]
            ),
            "admin": models.User(
                email=["dummy@admin.com"],
                is_admin=True
            ),
            "dummy_admin": models.User(
                email=["dummy3@admin.com"],
                is_admin=True
            )
        }

    def get(self, url, *args, **kwds):
        """
        Makes a get request.
        """
        url = url
        self.response = self.client.get(url, *args)

    def assertStatusCode(self, code): #pylint: disable=invalid-name
        self.assertEqual(self.response.status_code, code, self.response.headers)

    def setUp(self):
        super(SudoUnitTest, self).setUp()
        self.accounts = self.get_accounts()
        for user in self.accounts.values():
            user.put()
        self.user = None

    # User should be redirected to login.
    def testNoLogin(self):
        self.get('/sudo/su/dummy@student.com')
        self.assertStatusCode(302)

    def testLoginToSudo(self):
        self.login('admin')
        self.get('/sudo/su/dummy@student.com')
        self.assertStatusCode(200)
        self.logout()

    def testStudentAttemptToSudo(self):
        self.login('student1')
        self.get('/sudo/su/dummy@student.com')
        self.assertStatusCode(404)

    def testNonExistantStudent(self):
        self.login('admin')
        self.get('/sudo/su/nonexistant@student.com')
        self.assertStatusCode(404)

    def testCheckStudent2(self):
        self.login('staff')
        self.get('/sudo/su/other@student.com')
        self.assertStatusCode(404)


if __name__ == "__main__":
    unittest.main()
