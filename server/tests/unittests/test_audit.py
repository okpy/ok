#!/usr/bin/env python
# encoding: utf-8
#pylint: disable=no-member, no-init, too-many-public-methods
#pylint: disable=attribute-defined-outside-init
# This disable is because the tests need to be name such that
# you can understand what the test is doing from the method name.
#pylint: disable=missing-docstring
"""
tests.py

"""

from test_base import APIBaseTestCase, unittest #pylint: disable=relative-import

from google.appengine.ext import ndb

from app import models, api
from app.constants import ADMIN_ROLE

from test_api import make_fake_assignment, make_fake_course

class AuditTest(APIBaseTestCase): #pylint: disable=no-init
    """
    Tests that audit logs are correctly created for actions.
    """

    def setUp(self): #pylint: disable=super-on-old-class, invalid-name
        """Set up the API Test.

        Sets up the authenticator stub, and logs you in as an admin."""
        super(AuditTest, self).setUp()
        self.login('dummy_admin')
        self.api = api.GroupAPI()
        self.course = make_fake_course(self.user)
        self.course.put()
        self.assignment = make_fake_assignment(self.course, self.user)
        self.assignment.put()

        self.group = models.Group(
            assignment=self.assignment.key)
        self.group.put()

    def get_accounts(self):
        return {
            "dummy_admin": models.User(
                key=ndb.Key("User", "dummy@admin.com"),
                email="dummy@admin.com",
                first_name="Admin",
                last_name="Jones",
                login="albert",
                role=ADMIN_ROLE
            ),
            "dummy_student": models.User(
                key=ndb.Key("User", "dummy@student.com"),
                email="dummy@student.com",
                first_name="Student",
                last_name="Jones",
                login="billy",
            ),
            "student2": models.User(
                key=ndb.Key("User", "other@student.com"),
                email="other@student.com",
                first_name="Billy",
                last_name="Jones",
                login="biilly",
            ),
        }

    def set_data(self, data):
        self.api.parse_args = lambda index, user: data

    def test_remove_member(self):
        members = [self.accounts['dummy_student'].key]
        self.group.members = members
        self.group.put()

        data = {'member': members[0]}

        print self.user
        result = self.api.remove_member(self.group, self.user, data)

        audit_logs = models.AuditLog.query().fetch()
        self.assertEqual(len(audit_logs), 1)

        audit_log = audit_logs[0]
        self.assertEqual(audit_log.user, self.user.key)
        self.assertEqual(audit_log.obj, self.group.key)
        self.assertIn('Group', audit_log.event_type)
        self.assertIn('remove', audit_log.event_type)

    def test_add_member(self):
        members = [self.accounts['dummy_student'].key]
        data = {'member': members[0]}

        result = self.api.add_member(self.group, self.user, data)

        audit_logs = models.AuditLog.query().fetch()
        self.assertEqual(len(audit_logs), 1)

        audit_log = audit_logs[0]
        self.assertEqual(audit_log.user, self.user.key)
        self.assertEqual(audit_log.obj, self.group.key)
        self.assertIn('Group', audit_log.event_type)
        self.assertIn('add', audit_log.event_type)

if __name__ == '__main__':
    unittest.main()

