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

import datetime
from test_base import APIBaseTestCase, unittest, api #pylint: disable=relative-import
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils
from ddt import ddt, data, unpack
from app.exceptions import *
from integration.test_api_base import APITest


class FinalSubmissionAPITest(APIBaseTestCase):

	API = api.FinalSubmissionAPI

	def setUp(self):
		super(FinalSubmissionAPITest, self).setUp()
		self.user = self.accounts['dummy_admin']
		self.user1 = self.accounts['dummy_student']
		self.user2 = self.accounts['dummy_student2']
		self.user3 = self.accounts['dummy_student3']
		self.assignment_name = 'Hog Project'
		self._course = make_fake_course(self.user)
		self._course.put()
		self._assign = make_fake_assignment(self._course, self.user)
		self._assign.name = self._assign.display_name = self.assignment_name
		self._assign.put()
		self._backup = make_fake_backup(self._assign, self.user2)
		self._submission = make_fake_submission(self._backup)

	def get_accounts(self):
		return APITest().get_accounts()

	# test mark as final

	def test_mark_as_final(self):
		""" Tests that marking works, at the basic level """
		self.API().mark_backup(self.user, dict(backup=self._backup.key))

		assert models.FinalSubmission.query(
			models.FinalSubmission.submission==self._submission.key
		).get() is not None


	def test_ERROR_mark_as_final_backup(self):
		""" Tests that a missing backup raises the correct error. """
		try:
			key = self._backup.key
			key.delete()
			self.API().mark_backup(self.user, dict(backup=key))
		except BadValueError as e:
			self.assertEqual(str(e), 'No such backup exists.')

	def test_ERROR_mark_as_final_subm(self):
		""" Tests that a missing submission raises the correct error. """
		try:
			self._submission.key.delete()
			self.API().mark_backup(self.user, dict(backup=self._backup.key))
		except BadValueError as e:
			self.assertEqual(str(e), 'No such submission exists.')