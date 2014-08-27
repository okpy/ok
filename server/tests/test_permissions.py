#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

from test_base import BaseTestCase, unittest #pylint: disable=relative-import

from app import models
from app.needs import Need
from app.constants import ADMIN_ROLE, STAFF_ROLE #pylint: disable=import-error

from ddt import ddt, data

from google.appengine.ext import ndb

@ddt
class PermissionsUnitTest(BaseTestCase):
    def get_accounts(self):
        """
        Returns the accounts you want to exist in your system.
        """
        return {
            "student0": models.User(
                key=ndb.Key("User", "dummy@student.com"),
                email="dummy@student.com",
                first_name="Dummy",
                last_name="Jones",
                login="some13413"
            ),
            "student1": models.User(
                key=ndb.Key("User", "other@student.com"),
                email="other@student.com",
                first_name="Other",
                last_name="Jones",
                login="other13413",
            ),
            "staff": models.User(
                key=ndb.Key("User", "dummy@staff.com"),
                email="dummy@staff.com",
                first_name="Staff",
                last_name="Jones",
                login="alberto",
                role=STAFF_ROLE
            ),
            "empty_staff": models.User(
                key=ndb.Key("User", "dummy_empty@staff.com"),
                email="dummy_empty@staff.com",
                first_name="Staff",
                last_name="Empty",
                login="albertoo",
                role=STAFF_ROLE
            ),
            "admin": models.User(
                key=ndb.Key("User", "dummy@admin.com"),
                email="dummy@admin.com",
                first_name="Admin",
                last_name="Jones",
                login="albert",
                role=ADMIN_ROLE
            ),
            "anon": models.AnonymousUser,
        }

    def enroll(self, student, course):
        """Enroll student in course."""
        s = self.accounts[student]
        s.courses.append(self.courses[course].key)
        s.put()

    def teach(self, staff, course):
        """Add staff to the staff of course."""
        self.courses[course].staff.append(self.accounts[staff].key)
        self.courses[course].put()

    def setUp(self):
        super(PermissionsUnitTest, self).setUp()
        self.accounts = self.get_accounts()

        self.courses = {
            "first": models.Course(),
            "second": models.Course(),
            }

        for course in self.courses.values():
            course.put()

        self.enroll("student0", "first")
        self.enroll("student1", "second")
        self.teach("staff", "first")

        self.assignments = {
            "first": models.Assignment(
                name="first",
                points=3,
                creator=self.accounts["admin"].key
                ),
            "empty": models.Assignment(
                name="empty",
                points=3,
                creator=self.accounts["admin"].key
                ),
            }

        self.submissions = {
            "first": models.Submission(
                submitter=self.accounts["student0"].key,
                assignment=self.assignments["first"].key,
                messages="{}"
                ),
            "second": models.Submission(
                submitter=self.accounts["student1"].key,
                assignment=self.assignments["first"].key,
                messages="{}"
                ),
            }
        self.user = None

    def login(self, user):
        assert not self.user
        self.user = self.accounts[user]

    def logout(self):
        assert self.user
        self.user = None

    class PTest(object):
        """A test of wehther a user can access a model object with need."""
        def __init__(self, name, user, model, obj, need, output):
            self.__name__ = name
            self.input = (user, model, obj, need)
            self.output = output

    permission_tests = [
        PTest("student_get_own",
              "student0", "Submission", "first", "get", True),
        PTest("stuent_get_other",
              "student1", "Submission", "first", "get", False),
        PTest("staff_get_same_course",
              "staff", "Submission", "first", "get", True),
        PTest("staff_get_other_course",
              "staff", "Submission", "second", "get", False),
        PTest("admin_get_student0",
              "admin", "Submission", "first", "get", True),
        PTest("admin_get_student1",
              "admin", "Submission", "second", "get", True),
        PTest("admin_delete_own_student",
              "admin", "Submission", "first", "delete", False),
        PTest("staff_delete_own_student",
              "admin", "Submission", "first", "delete", False),
        PTest("student_delete_submission",
              "student0", "Submission", "first", "delete", False),
        PTest("student_modify_submission",
              "student0", "Submission", "first", "modify", False),
        PTest("g",
              "student0", "Assignment", "first", "get", True),
        PTest("anon_get_assignment",
              "anon", "Assignment", "first", "get", True),
        PTest("student_create_assignment",
              "student0", "Assignment", "first", "create", False),
        PTest("admin_create_assignment",
              "admin", "Assignment", "first", "create", True),
        PTest("admin_delete_normal",
              "admin", "Assignment", "first", "delete", False),
        PTest("staff_delete_normal",
              "staff", "Assignment", "first", "delete", False),
        PTest("admin_delete_empty",
              "admin", "Assignment", "empty", "delete", False),
        PTest("staff_delete_empty",
              "staff", "Assignment", "empty", "delete", False),
        PTest("staff_delete_empty",
              "empty_staff", "Assignment", "empty", "delete", False),
        PTest("anon_get_course",
              "anon", "Course", "first", "get", True),
        PTest("student_get_course",
              "student0", "Course", "first", "get", True),
        PTest("admin_get_course",
              "admin", "Course", "first", "get", True),
        PTest("student_create_course",
              "student0", "Course", "first", "create", False),
        PTest("student_delete_course",
              "student0", "Course", "first", "delete", False),
        PTest("staff_create_course",
              "staff", "Course", "first", "create", False),
        PTest("staff_delete_course",
              "staff", "Course", "first", "delete", False),
        PTest("admin_create_course",
              "admin", "Course", "first", "create", True),
        PTest("admin_delete_course",
              "admin", "Course", "first", "delete", True),
        PTest("student_modify_course",
              "student0", "Course", "first", "modify", False),
        PTest("staff_modify_course",
              "staff", "Course", "first", "modify", True),
        PTest("a",
              "student0", "User", "student0", "get", True),
        PTest("b",
              "student0", "User", "student1", "get", False),
        PTest("staff_get_other_user",
              "staff", "User", "student1", "get", False),
        PTest("staff_get_same_user",
              "staff", "User", "student0", "get", True),
        PTest("admin_get_student1",
              "admin", "User", "student1", "get", True),
        PTest("admin_create_student1",
              "admin", "User", "student1", "create", True),
    ]

    @data(*permission_tests)
    def testAccess(self, value):
        user_id, model, obj_name, need = value.input
        self.login(user_id) # sets self.user

        obj = None
        if model == "User":
            obj = self.accounts[obj_name]
        elif model == "Submission":
            obj = self.submissions[obj_name]
        elif model == "Assignment":
            obj = self.assignments[obj_name]
        elif model == "Course":
            obj = self.courses[obj_name]

        if not obj:
            self.assertTrue(False, "Invalid test arguments %s" % model)

        self.assertEqual(value.output, obj.can(self.user, Need(need), obj))

if __name__ == "__main__":
    unittest.main()
