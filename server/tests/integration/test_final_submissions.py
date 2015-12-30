#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=no-member, no-init, too-many-public-methods
# pylint: disable=attribute-defined-outside-init
# pylint: disable=missing-docstring, unused-import, invalid-name, import-error, super-on-old-class
"""Tests for final submissions."""

import os
os.environ['FLASK_CONF'] = 'TEST'
import datetime
NOW = datetime.datetime.now()

from test_base import APIBaseTestCase, unittest

from app import models, utils, constants, api

from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.ext import testbed

class FinalSubmissionTest(APIBaseTestCase):
    def get_accounts(self):
        """
        Returns the accounts you want to exist in your system.
        """
        keys = ["student0", "student1", "student2", "staff", "admin"]
        rval = {key: models.User(email=[key+"@b.edu"]) for key in keys}
        for k, val in rval.items():
            if 'admin' in k:
                val.is_admin = True
        return rval

    def setUp(self):
        super(FinalSubmissionTest, self).setUp()

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

        for student in ["student0", "student1", "student2"]:
            models.Participant.add_role(
                self.accounts[student], self.courses['first'], constants.STUDENT_ROLE)

        self.assignments = {
            "first": models.Assignment(
                name="first",
                points=3,
                creator=self.accounts["admin"].key,
                course=self.courses['first'].key,
                display_name="first display",
                templates="{}",
                max_group_size=3,
                due_date=NOW + datetime.timedelta(days=1),
                lock_date=NOW + datetime.timedelta(days=2)
                ),
            }
        for assign in self.assignments.values():
            assign.put()
        self.assign = self.assignments["first"]

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
            "late": models.Backup(
                submitter=self.accounts["student0"].key,
                assignment=self.assignments["first"].key,
                server_time = datetime.datetime.now() + datetime.timedelta(days=10),
                messages=[models.Message(
                    kind='file_contents', contents={"trends.py": ""})],
                ),

            }

        for backup in self.backups.values():
            backup.put()

    def run_deferred(self):
        """Execute all deferred tasks."""
        for task in self.taskqueue_stub.get_filtered_tasks():
            deferred.run(task.payload)

    def all_fs(self):
        return models.FinalSubmission.query().fetch()

    def assertNumFinalSubmissions(self, number):
        self.assertEqual(number, len(self.all_fs()))

    def assertNoFinalSubmissions(self):
        self.assertNumFinalSubmissions(0)

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

    def set_due_date(self, new_date):
        self.assign.due_date = new_date
        self.assign.put()

    def set_lock_date(self, lock_date):
        self.assign.lock_date = lock_date
        self.assign.put()

    def submit_json(self, assignment=None, messages=None):
        if not messages:
            messages = {'file_contents': {'submit': True, 'trends.py': 'hi!'}}

        if not assignment:
            assignment = self.assign

        self.post_json('/submission',
            data={'assignment': assignment.name,
                  'messages': messages})

    def submit(self, subm=None, is_final=True):
        """
        Submits the given submission.
        """
        if not subm:
            subm = self.backups['first']

        if not isinstance(subm, ndb.Key):
            subm = subm.key
        utils.assign_submission(subm.id(), True)

    def invite(self, inviter, invited):
        """|Inviter| invites |invited| to a group for self.assign."""
        invite_fn = models.Group.invite_to_group
        error = invite_fn(inviter.key, invited.email[0], self.assign)
        self.assertIsNone(error)
        return inviter.get_group(self.assign)

    def test_final_after_due_date(self):
        self.login('student0')
        self.set_due_date(NOW - datetime.timedelta(days=1))

        self.assertNoFinalSubmissions()

        # Submit
        self.submit_json()
        self.run_deferred()

        self.assertNoFinalSubmissions()

    def test_final_before_due_date(self):
        self.login('student0')
        self.set_due_date(NOW + datetime.timedelta(days=1))

        self.assertNoFinalSubmissions()

        # Submit
        self.submit()
        self.run_deferred()

        self.assertNumFinalSubmissions(1)

    def test_one_final(self):
        """An invite/accept/exit/invite sequence keeps a final submission."""
        self.login('student0')

        # Submit
        self.submit()
        self.run_deferred()

        finals = self.all_fs()
        self.assertEqual(1, len(finals))
        final = finals[0]
        subm = final.submission.get()
        self.assertIsNotNone(subm)
        backup = subm.backup.get()
        self.assertIsNotNone(backup)
        self.assertEqual(backup.submitter, self.user.key,
                "{} != {}".format(backup.submitter.get(), self.user))
        # TODO Not sure how to make/verify this final_submission get request...
        # self.assertEqual(final, self.user.get_final_submission(self.assign))
        # self.get('/user/{}/final_submission'.format(self.user.email[0]),
        #          data={'assignment': self.assign.key.id()})

        # Invite
        #invited = self.accounts['student1']
        # TODO This post is being made with admin as the user; not sure why...
        #self.post_json('/assignment/{}/invite'.format(self.assign.key.id()),
        #               data={'email': invited.email[0]})
        # TODO Check final submissions

        # Accept
        # TODO

        # Exit
        # TODO

        # Invite
        # TODO

    def test_set_different_submission_as_final_submission(self):
        self.login('student0')

        self.assertNoFinalSubmissions()

        # Submit
        self.submit()
        self.run_deferred()
        self.assertNumFinalSubmissions(1)

        self.logout()
        self.login('student1')
        self.set_due_date(NOW - datetime.timedelta(days=1))
        self.submit(self.backups['second'])
        self.run_deferred()

        self.assertNumFinalSubmissions(1)

        subm = models.Submission.query(
            models.Submission.backup == self.backups['second'].key
        ).get()

        api.FinalSubmissionAPI().post(
            self.user,
            dict(submission=subm.key))

        self.assertFinalSubmission(self.user, self.backups['second'])

    def test_set_different_backup_as_final_submission(self):
        self.login('student0')

        self.assertNoFinalSubmissions()

        # Submit
        self.submit()
        self.run_deferred()
        self.assertNumFinalSubmissions(1)

        self.logout()
        self.login('student1')
        self.set_due_date(NOW - datetime.timedelta(days=1))
        self.submit(self.backups['second'])
        self.run_deferred()

        self.assertNumFinalSubmissions(1)

        subm = models.Submission(backup=self.backups['second'].key)
        subm.put()

        api.FinalSubmissionAPI().post(self.user, dict(submission=subm.key))
        self.assertFinalSubmission(self.user, self.backups['second'])

    def test_revise_final_submission(self):
        self.login('student0')

        self.assertNoFinalSubmissions()

        # Submit
        self.submit(self.backups['first'])
        self.run_deferred()
        self.assertNumFinalSubmissions(1)
        self.assign.revision = True
        self.assign.put()
        self.set_due_date(NOW - datetime.timedelta(days=2))
        self.set_lock_date(NOW - datetime.timedelta(days=1))
        # This backup is now late (ignore the fact that it's the same backup)

        subm = models.Submission(backup=self.backups['late'].key)
        subm.put()

        api.FinalSubmissionAPI().post(self.user, dict(submission=subm.key))
        self.assertFinalSubmission(self.user, self.backups['first'])
        # Ensure the right revision is stored.
        fs = self.all_fs()[0]
        self.assertEqual(fs.revision, subm.key)


    def test_revisions_closed_final_submission(self):
        self.login('student0')
        self.assertNoFinalSubmissions()

        # Submit
        self.submit(self.backups['first'])
        self.run_deferred()
        self.assertNumFinalSubmissions(1)
        self.assign.revision = True
        self.assign.put()
        self.set_due_date(NOW - datetime.timedelta(days=2))
        self.set_lock_date(NOW - datetime.timedelta(days=1))
        # This backup is now late - but can be submitted as a revision
        subm = models.Submission(backup=self.backups['late'].key)
        subm.put()

        api.FinalSubmissionAPI().post(self.user, dict(submission=subm.key))
        self.assertFinalSubmission(self.user, self.backups['first'])
        # Ensure the right revision is stored.
        fs = self.all_fs()[0]
        self.assertEqual(fs.revision, subm.key)
        origRevision = subm

        # Close revision period
        self.assign.revision = False
        self.assign.put()
        # This backup is now late - and can't be submitted as a revision
        subm = models.Submission(backup=self.backups['first'].key)
        subm.put()
        try:
            api.FinalSubmissionAPI().post(self.user, dict(submission=subm.key))
        except ValueError as e:
            self.assertEqual(str(e), 'Cannot change submission after due date')

        self.set_lock_date(NOW + datetime.timedelta(days=1))


        api.FinalSubmissionAPI().post(self.user, dict(submission=subm.key))
        self.assertFinalSubmission(self.user, self.backups['first'])
        self.assertNumFinalSubmissions(1)
        # Ensure the right revision is stored.
        fs = self.all_fs()[0]
        self.assertEqual(fs.revision, origRevision.key)

    def test_create_group(self):
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

    def test_invite(self):
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

    def test_accept(self):
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

    def test_decline(self):
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

    def test_exit(self):
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

    ##############
    # SUBMIT NDB #
    ##############

    def test_ndb_submit(self):
        """ test backup modifications by ndb submit """
        datestr = '2015-04-20 00:00:00'
        datestr_converted = '2015-04-20 07:00:00'  # because GAE is stubborn
        backup = api.SubmitNDBImplementation().create_submission(
            self.accounts['student0'],
            self.assignments['first'],
            {'analytics': {'time': datestr}},
            True,
            self.accounts['student0'])
        self.assertEqual(backup.created, datetime.datetime.strptime(datestr_converted, '%Y-%m-%d %H:%M:%S'))

if __name__ == "__main__":
    unittest.main()
