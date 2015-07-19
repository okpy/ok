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

from ddt import ddt, data, unpack

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

class UserMergeTest(BaseUnitTest):
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

    def get_basic_user(self): #pylint: disable=no-self-use
        email = 'test@example.com'
        user = models.User(email=[email])
        user.put()

        return user

    def get_user_pair(self, typ="same"):
        user = self.get_basic_user()
        user2 = self.get_basic_user()
        if typ == "upper":
            user2.email[0] = user2.email[0][0].upper() + user2.email[0][1:]
            user2.put()

        return (user, user2)


    def merge_user(self, usera, userb): #pylint: disable=no-self-use
        utils.merge_user(usera, userb)

    def test_merge_user_lowercase(self):
        """
        Tests that two users with the same email (when lowercased) are merged.
        """
        user_obj, user_obj_upper = self.get_user_pair("upper")
        new_email = user_obj_upper.email[0]

        self.merge_user(user_obj, user_obj_upper)
        user_obj = user_obj.key.get()
        user_obj_upper = user_obj_upper.key.get()

        self.assertNotEqual(user_obj_upper.email[0], new_email)
        self.assertNotIn(new_email, user_obj.email)

    def test_merge_user_email(self):
        """
        Tests that the emails of two users gets merged correctly.
        """
        user_obj, user_obj2 = self.get_user_pair()
        new_email = user_obj2.email[0] = '123' + user_obj.email[0]
        user_obj2.put()

        self.merge_user(user_obj, user_obj2)
        user_obj = user_obj.key.get()
        user_obj2 = user_obj2.key.get()

        self.assertNotEqual(user_obj2.email[0], new_email)
        self.assertIn(new_email, user_obj.email)

    def test_leave_group(self):
        """
        Tests that merging two users makes the merged user leave groups.
        """
        user_obj, user_obj2 = self.get_user_pair()

        # Cause groups must have 2 people
        user_obj3 = self.get_basic_user()
        user_obj3.email = ['rawr@thing.com']
        user_obj3.put()
        user_obj4 = self.get_basic_user()
        user_obj4.email = ['doggy@thing.com']
        user_obj4.put()

        group = models.Group(
            member=[user_obj2.key, user_obj3.key, user_obj4.key],
            assignment=self.assign.key)
        group.put()

        self.merge_user(user_obj, user_obj2)

        group = group.key.get()
        self.assertIsNotNone(group)
        self.assertNotIn(user_obj2.key, group.member)

    def test_resubmit(self):
        user_obj, user_obj2 = self.get_user_pair()
        calls = [0]
        def resubmit(*args):
            calls[0] += 1

        self.mock(models.Submission, 'resubmit', resubmit)

        backup = models.Backup()
        backup.submitter = user_obj2.key
        backup.put()
        subm = models.Submission(backup=backup.key)
        subm.put()

        self.merge_user(user_obj, user_obj2)
        self.assertNotEqual(calls[0], 0)

    def test_no_resubmit(self):
        user_obj, user_obj2 = self.get_user_pair()

        calls = [0]
        def resubmit(*args):
            calls[0] += 1

        self.merge_user(user_obj, user_obj2)
        self.assertEqual(calls[0], 0)

    def test_no_resubmit_other_user(self):
        user_obj, user_obj2 = self.get_user_pair()
        calls = [0]
        def resubmit(*args):
            calls[0] += 1

        self.mock(models.Submission, 'resubmit', resubmit)

        backup = models.Backup()
        backup.submitter = user_obj.key
        backup.put()
        subm = models.Submission(backup=backup.key)
        subm.put()

        self.merge_user(user_obj, user_obj2)
        self.assertEqual(calls[0], 0)

    def test_audit_log(self):
        user_obj, user_obj2 = self.get_user_pair()

        self.merge_user(user_obj, user_obj2)
        log = models.AuditLog.query(
            models.AuditLog.event_type == "Merge user").get()
        self.assertIsNotNone(log)
        self.assertEqual(log.user, user_obj.key)
        self.assertEqual(log.obj, user_obj2.key)

    def test_inputs(self):
        user_obj, user_obj2 = self.get_user_pair()
        self.merge_user(user_obj, user_obj2)
        self.merge_user(user_obj.key, user_obj2)
        self.merge_user(user_obj, user_obj2.key)
        self.merge_user(user_obj.key, user_obj2.key)

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
        self.assertNotEqual(calls[0], 0)
        self.assertNotEqual(calls[1], 0)
        self.assertNotEqual(calls[2], 0)

@ddt
class UserCounterHelperTest(BaseUnitTest):
    class FakeQuery(object):
        def __init__(self, count):
            self._count = count

        def count(self, max_size):
            if max_size:
                return min(self._count, max_size)
            return self._count

    def run_counter(self, queries, limit=None):
        assignment = object()
        fake_self = object()
        def func(called_self, assign):
            self.assertEqual(assignment, assign)
            self.assertEqual(fake_self, called_self)
            return queries

        return models.make_num_counter(func)(fake_self, assignment, limit)

    @data(
        ((10, 2), None, 20),
        ((10, 2), 5, 5),
        ((10, 2), 6, 6),
        ((10, 5), 6, 6),
        ((1, 2), 5, 2),
        )
    @unpack
    def test_make_num_counter(self, params, limit, result):
        num_queries, query_size = params
        queries = [self.FakeQuery(query_size) for _ in range(num_queries)]

        answer = self.run_counter(queries, limit)
        self.assertEqual(result, answer)

if __name__ == "__main__":
    unittest.main()
