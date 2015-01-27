#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=invalid-name, too-many-public-methods, too-many-instance-attributes
# pylint: disable=no-self-use, attribute-defined-outside-init

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
        course_info = user.get_course_info(self.assign.course.get())
        current_assignment = None
        for assign_info in course_info['assignments']:
            if assign_info['assignment'].key == self.assign.key:
                current_assignment = assign_info
                break

        self.assertIsNotNone(current_assignment)
        self.assertEqual(current_assignment['backups'], True)
        self.assertEqual(current_assignment['submissions'], True)
        fs = current_assignment['final']['final_submission']
        self.assertIsNotNone(fs)
        if fs.group == None:
            self.assertEqual(fs.submitter, user.key)
        else:
            grp = user.get_group(self.assign.key)
            self.assertEqual(fs.group, grp.key)

        self.assertEqual(fs.submission.get().backup.get(), backup)

    def submit(self, subm):
        """
        Submits the given submission.
        """
        if not isinstance(subm, ndb.Key):
            subm = subm.key
        utils.assign_submission(subm.id(), True)

    def testFinalSubmissionMerging(self):
        """
        For bug 331.
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

        grp = models.Group(
            assignment=self.assignments['first'].key,
            member=[self.accounts['student0'].key,
                    self.accounts['student1'].key])
        grp.put()
        self.assertFinalSubmission('student0', 'first')

if __name__ == "__main__":
    unittest.main()
