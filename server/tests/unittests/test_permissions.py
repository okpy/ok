#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

import datetime

from test_base import BaseTestCase, unittest #pylint: disable=relative-import

from app import models
from app.needs import Need
from app.constants import STUDENT_ROLE, STAFF_ROLE #pylint: disable=import-error

from ddt import ddt

#pylint: disable=no-init, missing-docstring, no-member, too-many-instance-attributes
@ddt
class PermissionsUnitTest(BaseTestCase):
    @staticmethod
    def get_accounts():
        """
        Returns the accounts you want to exist in your system.
        """
        return {
            "student0": models.User(
                email=["dummy@student.com"],
            ),
            "student1": models.User(
                email=["other@student.com"],
            ),
            "student2": models.User(
                email=["otherrr@student.com"],
            ),
            "staff": models.User(
                email=["dummy@staff.com"],
            ),
            "empty_staff": models.User(
                email=["dummy_empty@staff.com"],
            ),
            "admin": models.User(
                email=["dummy@admin.com"],
                is_admin=True,
            ),
            "anon": models.User(
                email=["_anon"]
            ),
        }

    def enroll(self, student, course, role):
        """Enroll student in course with the given role."""
        part = models.Participant()
        part.user = self.accounts[student].key
        part.course = self.courses[course].key
        part.role = role
        part.put()

    def setUp(self): #pylint: disable=invalid-name
        super(PermissionsUnitTest, self).setUp()
        self.accounts = self.get_accounts()
        for user in self.accounts.values():
            user.put()

        self.courses = {
            "first": models.Course(
                institution="UC Awesome",
                instructor=[self.accounts['admin'].key]),
            "second": models.Course(
                institution="UC Awesome",
                instructor=[self.accounts['admin'].key]),
            }

        for course in self.courses.values():
            course.put()

        self.enroll("student0", "first", STUDENT_ROLE)
        self.enroll("student1", "first", STUDENT_ROLE)
        self.enroll("student2", "second", STUDENT_ROLE)
        self.enroll("staff", "first", STAFF_ROLE)

        self.assignments = {
            "first": models.Assignment(
                name="first",
                points=3,
                creator=self.accounts["admin"].key,
                course=self.courses['first'].key,
                display_name="first display",
                templates="{}",
                max_group_size=3,
                due_date=datetime.datetime.now()
                ),
            "empty": models.Assignment(
                name="empty",
                points=3,
                creator=self.accounts["admin"].key,
                course=self.courses['first'].key,
                display_name="second display",
                templates="{}",
                max_group_size=4,
                due_date=datetime.datetime.now()
                ),
            }
        for assign in self.assignments.values():
            assign.put()

        self.backups = {
            "first": models.Backup(
                submitter=self.accounts["student0"].key,
                assignment=self.assignments["first"].key,
                ),
            "second": models.Backup(
                submitter=self.accounts["student1"].key,
                assignment=self.assignments["first"].key,
                ),
            "third": models.Backup(
                submitter=self.accounts["student2"].key,
                assignment=self.assignments["first"].key,
                ),
            }

        self.groups = {
            'group1': models.Group(
                member=[self.accounts['student0'].key,
                        self.accounts['student1'].key],
                assignment=self.assignments['first'].key
            )}

        self.groups['group1'].put()

        group_submission = models.Backup(
            submitter=self.accounts['student0'].key,
            assignment=self.assignments['first'].key,
        )

        group_submission.put()
        self.backups['group'] = group_submission

        self.queues = {
            "first": models.Queue(
                assignment=self.assignments["first"].key,
                assigned_staff=[self.accounts["staff"].key],
            ),
        }
        for queue in self.queues.values():
            queue.put()

        self.diffs = {
            "first": models.Diff()
        }
        for diff in self.diffs.values():
            diff.put()

        self.comments = {
            "first": models.Comment(
                author=self.accounts['student0'].key,
                diff=self.diffs["first"].key,
                message="First comment"
            ),
        }
        for comment in self.comments.values():
            comment.put()

        self.user = None

    def login(self, user):
        assert not self.user
        self.user = self.accounts[user]

    def logout(self):
        assert self.user
        self.user = None

    #pylint: disable=too-few-public-methods
    class PTest(object):
        """A test of wehther a user can access a model object with need."""
        def __init__(self, name, user, model, obj, need, output): #pylint: disable=too-many-arguments
            self.__name__ = name
            self.input = (user, model, obj, need)
            self.output = output

   #  permission_tests = [
   #      PTest("anon_get_course",
   #            "anon", "Course", "first", "get", True),
   #      PTest("student_get_course",
   #            "student0", "Course", "first", "get", True),
   #      PTest("admin_get_course",
   #            "admin", "Course", "first", "get", True),
   #      PTest("student_create_course",
   #            "student0", "Course", "first", "create", False),
   #      PTest("student_delete_course",
   #            "student0", "Course", "first", "delete", False),
   #      PTest("staff_create_course",
   #            "staff", "Course", "first", "create", False),
   #      PTest("staff_delete_course",
   #            "staff", "Course", "first", "delete", False),
   #      PTest("admin_create_course",
   #            "admin", "Course", "first", "create", True),
   #      # TODO Perhaps admin shouldn't be able to delete a course so easily.
   #      PTest("admin_delete_course",
   #            "admin", "Course", "first", "delete", True),
   #      PTest("anon_delete_course",
   #            "anon", "Course", "first", "delete", False),
   #      PTest("student_modify_course",
   #            "student0", "Course", "first", "modify", False),
   #      PTest("staff_modify_course",
   #            "staff", "Course", "first", "modify", True),
   #      PTest("student_get_self",
   #            "student0", "User", "student0", "get", True),
   #      PTest("student_get_other",
   #            "student0", "User", "student1", "get", False),
   #      PTest("staff_get_user_wrong_course",
   #            "staff", "User", "student2", "get", False),
   #      PTest("staff_get_user",
   #            "staff", "User", "student0", "get", True),
   #      PTest("admin_get_student1",
   #            "admin", "User", "student1", "get", True),
   #      PTest("anon_get_student0",
   #            "anon", "User", "student0", "get", False),
   #      PTest("anon_get_student1",
   #            "anon", "User", "student1", "get", False),
   #      PTest("admin_create_student1",
   #            "admin", "User", "student1", "create", True),
   #  ]

    def access(self, value):
        user_id, model, obj_name, need = value.input
        self.login(user_id) # sets self.user

        obj = None
        if model == "User":
            obj = self.accounts[obj_name]
        elif model == "Backup":
            obj = self.backups[obj_name]
        elif model == "Assignment":
            obj = self.assignments[obj_name]
        elif model == "Course":
            obj = self.courses[obj_name]
        elif model == "Queue":
            obj = self.queues[obj_name]
        elif model == "Comment":
            obj = self.comments[obj_name]

        if not obj:
            self.assertTrue(False, "Invalid test arguments %s" % model)

        if need == "index":
            query = obj.__class__.query() #pylint: disable=maybe-no-member
            query = obj.can(self.user, Need(need), obj, query=query)

            if not query:
                self.assertFalse(value.output, "|can| method returned false.")
                return

            queried_data = query.fetch()

            if value.output:
                self.assertIn(obj, queried_data)
            else:
                self.assertNotIn(obj, queried_data)
        else:
            self.assertEqual(value.output, obj.can(self.user, Need(need), obj))

if __name__ == "__main__":
    unittest.main()
