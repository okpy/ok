#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

import os
os.environ['FLASK_CONF'] = 'TEST'
import datetime

from test_base import APIBaseTestCase, unittest #pylint: disable=relative-import

from app import models, utils

from google.appengine.ext import ndb

class PermissionsUnitTest(APIBaseTestCase):
    def get_accounts(self):
        """
        Returns the accounts you want to exist in your system.
        """
        return {
            "student0": models.User(
                email=["dummy@student.com"]
            ),
            "student1": models.User(
                email=["other@student.com"]
            ),
            "student2": models.User(
                email=["otherrr@student.com"]
            ),
            "staff": models.User(
                email=["dummy@staff.com"]
            ),
            "empty_staff": models.User(
                email=["dummy_empty@staff.com"]
            ),
            "admin": models.User(
                email=["dummy@admin.com"]
            )
        }

    def setUp(self):
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
        for v in self.assignments.values():
            v.put()

        self.backups = {
            "first": models.Backup(
                submitter=self.accounts["student0"].key,
                assignment=self.assignments["first"].key,
                messages=[models.Message(
                    kind='file_contents', contents={"trends.py": ""})],
                ),
            "second": models.Backup(
                submitter=self.accounts["student1"].key,
                assignment=self.assignments["first"].key,
                messages=[models.Message(
                    kind='file_contents', contents={"trends.py": ""})],
                ),
            "third": models.Backup(
                submitter=self.accounts["student2"].key,
                assignment=self.assignments["first"].key,
                messages=[models.Message(
                    kind='file_contents', contents={"trends.py": ""})],
                ),
            }

        for backup in self.backups.values():
            backup.put()

        self.submissions = {
                "first": models.Submission(
                    backup=self.backups["first"].key
                    ),
                "second": models.Submission(
                    backup=self.backups["second"].key
                    )
            }

        for subm in self.submissions.values():
            subm.put()

        self.groups = {
            'group1': models.Group(
                member=[self.accounts['student0'].key,
                         self.accounts['student1'].key],
                assignment=self.assignments['first'].key
            )}

        self.groups['group1'].put()
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
        self.assertEquals(num, subms.count())

    def submit(self, subm):
        utils.assign_submission(subm.key.id(), True)

    def testFirstSubmission(self):
        self.login('student0')
        self.set_assignment('first')
        self.assertNoSubmissions()
        self.submit(self.submissions['first'])
        self.assertNumSubmissions(1)


if __name__ == "__main__":
    print 'test disabled for now'
    return
    unittest.main()
