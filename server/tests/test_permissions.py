#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

from test_base import BaseTestCase, unittest #pylint: disable=relative-import

from app import models
from app.needs import Need
from app.constants import ADMIN_ROLE, STAFF_ROLE #pylint: disable=import-error

from ddt import ddt, file_data, unpack

from google.appengine.ext import ndb

@ddt
class PermissionsUnitTest(BaseTestCase):
    def get_accounts(self):
        """
        Returns the accounts you want to exist in your system.
        """
        return {
            "dummy_student": models.User(
                key=ndb.Key("User", "dummy@student.com"),
                email="dummy@student.com",
                first_name="Dummy",
                last_name="Jones",
                login="some13413"
            ),
            "other_student": models.User(
                key=ndb.Key("User", "other@student.com"),
                email="other@student.com",
                first_name="Other",
                last_name="Jones",
                login="other13413",
            ),
            "dummy_staff": models.User(
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
            "dummy_admin": models.User(
                key=ndb.Key("User", "dummy@admin.com"),
                email="dummy@admin.com",
                first_name="Admin",
                last_name="Jones",
                login="albert",
                role=ADMIN_ROLE
            ),
            "anon": models.AnonymousUser,
        }

    def setUp(self):
        super(PermissionsUnitTest, self).setUp()
        self.accounts = self.get_accounts()

        self.courses = {
                "first": models.Course(),
                "second": models.Course(),
            }

        for course in self.courses.values():
            course.put()

        self.accounts['dummy_student'].courses.append(self.courses['first'].key)
        self.accounts['dummy_student'].put()

        self.courses['first'].staff.append(self.accounts['dummy_staff'].key)
        self.courses['first'].put()

        self.accounts['other_student'].courses.append(
            self.courses['second'].key)
        self.accounts['other_student'].put()

        self.assignments = {
            "first": models.Assignment(
                name="first",
                points=3,
                creator=self.accounts['dummy_admin'].key
                ),
            "empty": models.Assignment(
                name="empty",
                points=3,
                creator=self.accounts['dummy_admin'].key
                ),
            }

        self.submissions = {
            "first": models.Submission(
                submitter=self.accounts["dummy_student"].key,
                assignment=self.assignments["first"].key,
                messages="{}"
                ),
            "second": models.Submission(
                submitter=self.accounts["other_student"].key,
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

    @file_data('permissions_tests.json')
    def testAccess(self, value):
        user_id, obj, need, result = value
        self.login(user_id)

        model, args = obj
        if model == 'User':
            obj = self.accounts[args]
        elif model == "Submission":
            obj = self.submissions[args]
        elif model == "Assignment":
            obj = self.assignments[args]
        elif model == "Course":
            obj = self.courses[args]
        else:
            self.assertTrue(False, "Invalid test arguments %s" % model)

        self.assertEqual(result, obj.can(self.user, Need(need), obj),
                value)

   #  def testUserCanGetSelf(self):
   #      self.login('dummy_student')
   #      self.assertTrue(self.user.can(self.user, Need('get')))

   #  def testUserCannotGetOther(self):
   #      self.login('dummy_student')
   #      other = self.accounts['other_student']

   #      self.assertFalse(self.user.can(other, Need('get')))
   #      permissions_tests.json
   #  def test_get_non_admin(self):
   #      """Tests that a get with a student access token works."""
   #      self.get('/{}'.format(self.name))
   #      self.assertStatusCode(200)

if __name__ == '__main__':
    unittest.main()
