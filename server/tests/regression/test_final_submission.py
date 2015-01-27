#!/usr/bin/env python
# encoding: utf-8

# pylint: disable=invalid-name, too-many-public-methods, too-many-instance-attributes, no-self-use, attribute-defined-outside-init, no-member, no-init, locally-disabled, missing-docstring

"""
Tests for the permissions system
"""

import os
os.environ['FLASK_CONF'] = 'TEST'
import datetime

from test_base import APIBaseTestCase, unittest #pylint: disable=relative-import

from app import models, utils

from google.appengine.ext import ndb

class FinalSubmissionTest(APIBaseTestCase):
    def get_accounts(self):
        """
        Returns the accounts you want to exist in your system.
        """
        return {
            "student0": models.User(
                email=["student0@student.com"]
            ),
            "student1": models.User(
                email=["student1@student.com"]
            ),
            "student2": models.User(
                email=["sudent2@student.com"]
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
        super(FinalSubmissionTest, self).setUp()
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
        for assign in self.assignments.values():
            assign.put()

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
        self.user = self.accounts['student0']
        self.assign = self.assignments['first']


    def set_assignment(self, assign):
        if isinstance(assign, (str, unicode)):
            assign = self.assignments[assign]
        self.assign = assign

    def assertNoFinalSubmission(self, user):
        """
        Asserts that the |user| has no final submissions.
        """
        self.assertNumFinalSubmissions(user, 0)

    def assertNumFinalSubmissions(self, user, num):
        """
        Asserts that the |user| has |num| final submissions.
        """
        FS = models.FinalSubmission
        subms = FS.query()
        subms = subms.filter(FS.assignment == self.assign.key)
        subms = subms.filter(
            FS.group == user.get_group(self.assign.key).key)
        self.assertEquals(num, subms.count())

    def assertFinalSubmission(self, user, backup):
        """
        Asserts that the |user| has the final submission which corresponds
        to |backup|.
        """
        if isinstance(user, str):
            user = self.accounts[user]
        final = user.get_final_submission(self.assign.key)
        self.assertIsNotNone(final)
        self.assertEqual(backup.key, final.submission.get().backup)

    def submit(self, subm):
        """
        Submits the given submission.
        """
        if not isinstance(subm, ndb.Key):
            subm = subm.key
        utils.assign_submission(subm.id(), True)

    def testFinalSubmissionMerging(self):
        """
        Tests that merging groups keeps the final submission for that group.
        """
        self.set_assignment('first')

        self.groups['group1'].key.delete()

        subm = self.submissions['first']
        subm.key.delete()
        self.submit(self.backups['first'])
        self.assertFinalSubmission(
            self.accounts['student0'],
            self.backups['first'])

        group = models.Group(
            assignment=self.assignments['first'].key,
            member=[self.accounts['student0'].key,
                    self.accounts['student1'].key])
        group.put()
        for user in (self.accounts['student0'], self.accounts['student1']):
            user.update_final_submission(self.assign)
        self.assertFinalSubmission('student0', 'first')
        self.assertFinalSubmission('student1', 'first')

if __name__ == "__main__":
    unittest.main()
