#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

import datetime

from test_base import APIBaseTestCase, unittest #pylint: disable=relative-import

from app import models, utils
from app.constants import ADMIN_ROLE, STAFF_ROLE #pylint: disable=import-error

from google.appengine.ext import ndb

class PermissionsUnitTest(APIBaseTestCase):
    def get_accounts(self):
        """
        Returns the accounts you want to exist in your system.
        """
        return {
            'student0': models.User(
                key=ndb.Key('User', 'dummy@student.com'),
                email='dummy@student.com',
                first_name='Dummy',
                last_name='Jones',
                login='some13413'
            ),
            'student1': models.User(
                key=ndb.Key('User', 'other@student.com'),
                email='other@student.com',
                first_name='Other',
                last_name='Jones',
                login='other13413',
            ),
            'student2': models.User(
                key=ndb.Key('User', 'otherrr@student.com'),
                email='otherrr@student.com',
                first_name='Otherrrrr',
                last_name='Jones',
                login='otherrr13413',
            ),
            'staff': models.User(
                key=ndb.Key('User', 'dummy@staff.com'),
                email='dummy@staff.com',
                first_name='Staff',
                last_name='Jones',
                login='alberto',
                role=STAFF_ROLE
            ),
            'empty_staff': models.User(
                key=ndb.Key('User', 'dummy_empty@staff.com'),
                email='dummy_empty@staff.com',
                first_name='Staff',
                last_name='Empty',
                login='albertoo',
                role=STAFF_ROLE
            ),
            'admin': models.User(
                key=ndb.Key('User', 'dummy@admin.com'),
                email='dummy@admin.com',
                first_name='Admin',
                last_name='Jones',
                login='albert',
                role=ADMIN_ROLE
            ),
            'anon': models.AnonymousUser()
        }

    def get_courses(self):
        return {
            'first': models.Course(
                name='first',
                institution='UC Awesome',
                year='2015',
                term='Spring',
                creator=self.accounts['admin'].key),
            'second': models.Course(
                name='second',
                institution='UC Awesome',
                year='2015',
                term='Spring',
                creator=self.accounts['admin'].key),
        }

    def get_assignments(self):
        return {
            'first': models.Assignment(
                name='first',
                points=3,
                creator=self.accounts['admin'].key,
                course=self.courses['first'].key,
                display_name='first display',
                templates='{}',
                max_group_size=3,
                due_date=datetime.datetime.now()
                ),
            'empty': models.Assignment(
                name='empty',
                points=3,
                creator=self.accounts['admin'].key,
                course=self.courses['first'].key,
                display_name='second display',
                templates='{}',
                max_group_size=4,
                due_date=datetime.datetime.now()
                )
        }

    def get_submissions(self):
        return {
            'first': models.Submission(
                submitter=self.accounts['student0'].key,
                assignment=self.assignments['first'].key,
                messages=[models.Message(
                    kind='file_contents', contents={'trends.py': ''})]
                ),
            'second': models.Submission(
                submitter=self.accounts['student1'].key,
                assignment=self.assignments['first'].key,
                messages=[models.Message(
                    kind='file_contents', contents={'trends.py': ''})]
                ),
            'third': models.Submission(
                submitter=self.accounts['student2'].key,
                assignment=self.assignments['first'].key,
                messages=[models.Message(
                    kind='file_contents', contents={'trends.py': ''})]
                )
        }

    def get_groups(self):
        return {
            'group1': models.Group(
                members=[self.accounts['student0'].key,
                         self.accounts['student1'].key],
                assignment=self.assignments['first'].key
            )
        }

    def setUp(self):
        super(PermissionsUnitTest, self).setUp()
        self.accounts = self.get_accounts()
        for user in self.accounts.values():
            user.put()

        self.courses = self.get_courses()

        for course in self.courses.values():
            course.put()

        self.assignments = self.get_assignments()
        for assgn in self.assignments.values():
            assgn.put()

        self.submissions = self.get_submissions()
        for subm in self.submissions.values():
            subm.put()

        self.groups = self.get_groups()
        for group in self.groups.values():
            group.put()

        self.user = None

    def set_assignment(self, assign):
        self.assign = self.assignments[assign]

    def assertNoSubmissions(self):
        self.assertNumSubmissions(0)

    def assertNumSubmissions(self, num):
        FS = models.FinalSubmission
        subms = FS.query()
        subms = subms.filter(FS.assignment == self.assign.key)
        subms = subms.filter(FS.group == self.user.get_group(self.assign.key).key)
        subms = list(subms)
        self.assertEquals(num, len(subms))

    def submit(self, subm):
        utils.assign_submission(subm.key.id())

    def testFirstSubmission(self):
        self.login('student0')
        self.set_assignment('first')
        self.assertNoSubmissions()
        self.submit(self.submissions['first'])
        self.assertNumSubmissions(1)


if __name__ == '__main__':
    unittest.main()
