#!/usr/bin/env python
# encoding: utf-8
"""
Tests api auto updating
"""
import os
os.environ['FLASK_CONF'] = 'TEST'
import datetime

from test_base import APIBaseTestCase, unittest
from test_base import make_fake_assignment, make_fake_course
from app import models
from app.urls import check_version, IncorrectVersionError

class AutoUpdateTest(APIBaseTestCase):
    """
    Tests for client auto-updating
    """

    def get_accounts(self):
        return {}

    def setUp(self):
        super(AutoUpdateTest, self).setUp()
        due_date = datetime.datetime.now() + datetime.timedelta(days=2)
        self.user = models.User.get_or_insert('test@example.com')

        self.course = make_fake_course(self.user)
        self.course.put()

        self.assignment = make_fake_assignment(self.course, self.user)
        self.assignment.put()

        self.version = models.Version.get_or_insert('ok', base_url="https://www.baseurl.com")
        self.invalid = False

    def try_request(self, version):
        try:
            self.message = check_version(version)
            self.invalid = False
        except IncorrectVersionError:
            self.invalid = True

    def add_version(self, version):
        self.version.versions.append(version)
        self.version.put()

    def set_version(self, version):
        self.version.current_version = version
        self.version.put()

    def add_and_set_version(self, version):
        self.add_version(version)
        self.set_version(version)

    def assertAccessOk(self):
        self.assertEqual(self.invalid, False)

    def assertAccessInvalid(self):
        self.assertEqual(self.invalid, True)

    def test_basic_access(self):
        self.add_and_set_version('1.0.0')
        self.try_request('1.0.0')
        self.assertAccessOk()

    def test_invalid_access(self):
        self.add_and_set_version('1.1.0')
        self.try_request('1.0.0')
        self.assertAccessInvalid()

    def test_pick_correct_versio(self):
        self.add_version('1.0.0')
        self.add_version('1.1.0')
        self.set_version('1.0.0')
        self.try_request('1.1.0')
        self.assertAccessInvalid()


if __name__ == '__main__':
    unittest.main()

