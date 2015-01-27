#!/usr/bin/env python
# encoding: utf-8

# pylint: disable=invalid-name, too-many-public-methods, too-many-instance-attributes, no-self-use, attribute-defined-outside-init, no-member, no-init, locally-disabled, missing-docstring

"""
Tests for the permissions system
"""

import os
os.environ['FLASK_CONF'] = 'TEST'
import datetime

from test_base import BaseTestCase, unittest #pylint: disable=relative-import

from app import models, utils, constants

from google.appengine.ext import ndb

class FinalSubmissionTest(BaseTestCase):
    def create_accounts(self):
        """
        Returns the accounts you want to exist in your system.
        """
        keys = ["student0", "student1", "student2", "staff", "admin"]
        return {key: models.User.get_or_insert(key+"@b.edu") for key in keys}

    def setUp(self):
        super(FinalSubmissionTest, self).setUp()
        self.accounts = self.create_accounts()

        self.courses = {
            "first": models.Course(
                institution="UC Awesome",
                display_name="First Course",
                instructor=[self.accounts['admin'].key]),
            "second": models.Course(
                institution="UC Awesome",
                display_name="Second Course",
                instructor=[self.accounts['admin'].key]),
            }

        for course in self.courses.values():
            course.put()

        # Enroll students 0 and 1 in First Course.
        for student in [self.accounts[s] for s in ('student0', 'student1')]:
            c = self.courses['first'].key
            models.Participant.add_role(student.key, c, constants.STUDENT_ROLE)

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

        self.user = self.accounts['student0']
        self.assign = self.assignments['first']

    def set_assignment(self, assign):
        if isinstance(assign, (str, unicode)):
            assign = self.assignments[assign]
        self.assign = assign

    def assertFinalSubmission(self, user, backup):
        """
        Asserts that the |user| has the final submission which corresponds
        to |backup|.
        """
        if isinstance(user, (str, unicode)):
            user = self.accounts[user]
        final = user.get_final_submission(self.assign.key)
        if backup:
            self.assertIsNotNone(final)
            self.assertEqual(backup, final.submission.get().backup.get())
        else:
            self.assertIsNone(final)

    def submit(self, subm):
        """
        Submits the given submission.
        """
        if not isinstance(subm, ndb.Key):
            subm = subm.key
        utils.assign_submission(subm.id(), True)

    def invite(self, inviter, invited):
        """|Inviter| invites |invited| to a group for self.assign."""
        invite_fn = models.Group.invite_to_group
        error = invite_fn(inviter.key, invited.email[0], self.assign)
        self.assertIsNone(error)
        return inviter.get_group(self.assign)

    def testCreateGroup(self):
        """Merging groups keeps the final submission for that group."""
        self.submit(self.backups['first'])
        self.assertFinalSubmission('student0', self.backups['first'])
        self.assertFinalSubmission('student1', None)

        members = [self.accounts[s].key for s in ('student0', 'student1')]
        models.Group(assignment=self.assign.key, member=members).put()
        for member in members:
            member.get().update_final_submission(self.assign)

        self.assertFinalSubmission('student0', self.backups['first'])
        self.assertFinalSubmission('student1', self.backups['first'])

    def testInvite(self):
        """Final submission updates when a group is created."""
        self.submit(self.backups['first'])
        self.submit(self.backups['second'])
        self.assertFinalSubmission('student0', self.backups['first'])
        self.assertFinalSubmission('student1', self.backups['second'])

        inviter, invited = [self.accounts[s] for s in ('student0', 'student1')]
        self.invite(inviter, invited)

        self.assertFinalSubmission('student0', self.backups['first'])
        self.assertFinalSubmission('student1', self.backups['second'])
        final = inviter.get_final_submission(self.assign)
        self.assertIsNotNone(final.group)

    def testAccept(self):
        """Only one final submission after a group is formed."""
        self.submit(self.backups['first'])  # earlier (discard)
        self.submit(self.backups['second']) # later (keep)
        self.assertFinalSubmission('student0', self.backups['first'])
        self.assertFinalSubmission('student1', self.backups['second'])
        self.assertEqual(2, len(models.FinalSubmission.query().fetch()))

        inviter, invited = [self.accounts[s] for s in ('student0', 'student1')]
        group = self.invite(inviter, invited)
        self.assertIsNone(group.accept(invited))

        self.assertFinalSubmission('student0', self.backups['second'])
        self.assertFinalSubmission('student1', self.backups['second'])
        self.assertEqual(1, len(models.FinalSubmission.query().fetch()))

    def testDecline(self):
        """Final submissions are separate after a declined invitation."""
        self.submit(self.backups['first'])
        self.submit(self.backups['second'])

        inviter, invited = [self.accounts[s] for s in ('student0', 'student1')]
        group = self.invite(inviter, invited)
        self.assertIsNone(group.exit(invited))
        self.assertIsNone(inviter.get_group(self.assign))
        self.assertIsNone(invited.get_group(self.assign))

        self.assertFinalSubmission('student0', self.backups['first'])
        self.assertFinalSubmission('student1', self.backups['second'])
        self.assertEqual(2, len(models.FinalSubmission.query().fetch()))
        self.assertIsNone(inviter.get_final_submission(self.assign).group)
        self.assertIsNone(invited.get_final_submission(self.assign).group)

    def testExit(self):
        """A new final submission is created for an exiting member."""
        self.submit(self.backups['first'])
        self.submit(self.backups['second'])
        self.assertEqual(2, len(models.FinalSubmission.query().fetch()))

        # Invite and accept
        inviter, invited = [self.accounts[s] for s in ('student0', 'student1')]
        group = self.invite(inviter, invited)
        self.assertIsNone(group.accept(invited))
        self.assertEqual(1, len(models.FinalSubmission.query().fetch()))

        self.assertIsNone(group.exit(inviter))

        self.assertFinalSubmission('student0', self.backups['first'])
        self.assertFinalSubmission('student1', self.backups['second'])
        self.assertEqual(2, len(models.FinalSubmission.query().fetch()))
        self.assertIsNone(inviter.get_final_submission(self.assign).group)
        self.assertIsNone(invited.get_final_submission(self.assign).group)



if __name__ == "__main__":
    unittest.main()
