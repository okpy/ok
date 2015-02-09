#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=invalid-name, import-error

"""
Tests for the permissions system
"""

import os
os.environ['FLASK_CONF'] = 'TEST'
import unittest
from test_permissions import PermissionsUnitTest, BaseUnitTest, BaseTestCase
from test_base import make_fake_assignment, make_fake_course

from ddt import ddt, data

from app import utils, models
from app.models import ndb

PTest = PermissionsUnitTest.PTest
USER_TESTS = [
    PTest("student_get_self",
          "student0", "User", "student0", "get", True),
    PTest("student_get_other",
          "student0", "User", "student1", "get", False),
    PTest("staff_get_user_wrong_course",
          "staff", "User", "student2", "get", False),
    PTest("staff_get_user",
          "staff", "User", "student0", "get", True),
    PTest("admin_get_student1",
          "admin", "User", "student1", "get", True),
    PTest("anon_get_student0",
          "anon", "User", "student0", "get", False),
    PTest("anon_get_student1",
          "anon", "User", "student1", "get", False),
    PTest("admin_create_student1",
          "admin", "User", "student1", "create", True),
]

#pylint: disable=no-init, missing-docstring, too-many-public-methods
@ddt
class UserPermissionsUnitTest(PermissionsUnitTest):
    @data(*USER_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

class UserUniquenessTest(BaseUnitTest):
    def setUp(self):
        BaseTestCase.setUp(self)
        self._caught_exception = None
        self.user = self.get_basic_user()
        self.admin = models.User(email=['test@admin.com'], is_admin=True)
        self.admin.put()

        self.course = make_fake_course(self.admin)
        self.course.put()
        self.assign = make_fake_assignment(self.course, self.admin)
        self.assign.put()

    def tearDown(self):
        super(UserUniquenessTest, self).tearDown()
        self.assertNoException()

    def check_user_maker(called_func): #pylint: disable=no-self-argument
        def wrapped(self, user_id):
            if isinstance(user_id, ndb.Key):
                user_id = user_id.get()

            try:
                called_func(user_id)
            except Exception as e: #pylint: disable=broad-except
                self._caught_exception = e #pylint: disable=protected-access
        return wrapped

    check_user_email = check_user_maker(utils.unique_email_address)
    check_user_final = check_user_maker(utils.unique_group)
    check_user_group = check_user_maker(utils.unique_final_submission)

    def get_basic_user(self): #pylint: disable=no-self-use
        email = 'test@example.com'
        user = models.User(email=[email])
        user.put()

        return user

    def assertNoException(self):
        self.assertEqual(
            self._caught_exception, None, "Unexpected exception: {}".format(
                self._caught_exception))

    def assertNumGroups(self, user, assignment, num):
        G = models.Group
        groups = G.query(
            G.member == user.key, G.assignment == assignment.key).fetch()
        self.assertEqual(len(groups), num)

    def assertNumFS(self, user, assignment, num):
        FS = models.FinalSubmission
        subms = FS.query(
            FS.submitter == user.key, FS.assignment == assignment.key).fetch()
        self.assertEqual(len(subms), num)

    def assertNumUsers(self, user, num):
        U = models.User
        found = []
        for email in user.email:
            users = U.query(U.email == email).fetch()
            for u in users:
                found.append(u)

        self.assertEqual(len(found), num)

    def test_user_unique_email_single_user(self):
        self.check_user_email(self.user)
        self.assertNumUsers(self.user, 1)
        self.assertNumFS(self.user, self.assign, 0)
        self.assertNumGroups(self.user, self.assign, 0)

    def test_user_unique_group_single_user(self):
        self.check_user_group(self.user)
        self.assertNumUsers(self.user, 1)
        self.assertNumFS(self.user, self.assign, 0)
        self.assertNumGroups(self.user, self.assign, 0)

    def test_user_unique_final_single_user(self):
        self.check_user_final(self.user)
        self.assertNumUsers(self.user, 1)
        self.assertNumFS(self.user, self.assign, 0)
        self.assertNumGroups(self.user, self.assign, 0)

    def test_call_functions(self):
        user_obj = models.User(email=['test@example.com'])
        user_obj.put()
        calls = [0, 0, 0]
        def unique_email_address_mock(user):
            self.assertEqual(user, user_obj)
            calls[0] += 1
        self.mock(utils, 'unique_email_address', unique_email_address_mock)

        def unique_final_submission_mock(user):
            self.assertEqual(user, user_obj)
            calls[1] += 1
        self.mock(
            utils, 'unique_final_submission', unique_final_submission_mock)

        def unique_group_mock(user):
            self.assertEqual(user, user_obj)
            calls[2] += 1

        self.mock(utils, 'unique_group', unique_group_mock)

        utils.deferred_check_user(user_obj.key.id())
        self.assertEqual(calls[0], 1)
        self.assertEqual(calls[1], 1)
        self.assertEqual(calls[2], 1)

if __name__ == "__main__":
    unittest.main()
