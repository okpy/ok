#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

from test_base import BaseTestCase, unittest #pylint: disable=relative-import

from app import models
from app.needs import Need
from app.constants import ADMIN_ROLE #pylint: disable=import-error

from ddt import ddt, file_data, unpack

from google.appengine.ext import ndb

@ddt
class UserPermissionsUnitTest(BaseTestCase):
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
                login="other13413"
            ),
            "dummy_admin": models.User(
                key=ndb.Key("User", "dummy@admin.com"),
                email="dummy@admin.com",
                first_name="Admin",
                last_name="Jones",
                login="albert",
                role=ADMIN_ROLE
            ),
        }

    def setUp(self):
        super(UserPermissionsUnitTest, self).setUp()
        self.accounts = self.get_accounts()

        self.assignments = {
            "first": models.Assignment(
                name="first",
                points=3,
                creator=self.accounts['dummy_admin'].key
                )    
            }

        self.submissions = {
            "first": models.Submission(
                submitter=self.accounts["dummy_student"].key,
                assignment=self.assignments["first"].key,
                messages="{}"
                )    
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
        else:
            self.assertTrue(False, "Invalid test arguments")

        self.assertEqual(result, obj.can(self.user, Need(need)))

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

   #  def test_different_user(self):
   #      """One student can't see another user's submissions."""
   #      inst = self.get_basic_instance()
   #      inst.put()
   #      fake_user = models.User(email='gaga@gmail.com')
   #      inst2 = models.Submission(messages="{}",
   #                                submitter=fake_user.key,
   #                                assignment=self._assign.key)
   #      inst2.put()
   #      self.get_index()
   #      self.assertJson([inst.to_json()])
   #      self.assertTrue(inst2.to_json() not in self.response_json)

if __name__ == '__main__':
    unittest.main()
