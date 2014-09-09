#!/usr/bin/env python
# encoding: utf-8
"""
Tests api field filtering.
"""
from test_base import APIBaseTestCase, unittest
from app import models
from app.urls import check_version

class AutoUpdateTest(APIBaseTestCase):
    """
    Tests for client auto-updating
    """

    def get_accounts(self):
        pass

    def setUp(self):
        super(AutoUpdateTest, self).setUp()
        self.assignment = models.Assignment(name='testassign')
        self.assignment.put()
        self.version = models.Version.get_or_insert('okpy')

    def try_request(self, version):
        self.message = check_version(version)

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
        self.assertEqual(self.message, None)

    def assertAccessInvalid(self):
        self.assertNotEqual(self.message, None)

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

