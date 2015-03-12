#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=no-member, no-init, too-many-public-methods
# pylint: disable=attribute-defined-outside-init
# pylint: disable=missing-docstring, unused-import, invalid-name, import-error, super-on-old-class
"""Tests for final submissions."""

import os
os.environ['FLASK_CONF'] = 'TEST'
import datetime

from test_base import APIBaseTestCase, unittest

from app import models, utils, constants

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
                due_date=datetime.datetime.now()
                ),
            }
        for assign in self.assignments.values():
            assign.put()
        self.assign = self.assignments["first"]

    def run_deferred(self):
        """Execute all deferred tasks."""
        for task in self.taskqueue_stub.get_filtered_tasks():
            deferred.run(task.payload)

    def test_one_final(self):
        """An invite/accept/exit/invite sequence keeps a final submission."""
        self.login('student0')

        # Submit
        messages = {'file_contents': {'submit': True, 'trends.py': 'hi!'}}
        self.post_json('/submission',
            data={'assignment': self.assign.name,
                  'messages': messages})
        self.run_deferred()

        finals = list(models.FinalSubmission.query().fetch())
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

if __name__ == "__main__":
    unittest.main()
