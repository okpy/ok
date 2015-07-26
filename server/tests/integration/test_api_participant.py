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


class ParticipantAPITest(APIBaseTestCase):

	API = api.ParticipantAPI

	def setUp(self):
		super(ParticipantAPITest, self).setUp()
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
		self._finalsubmission = make_fake_finalsubmission(self._submission, self._assign, self.user2)

	def get_accounts(self):
		return APITest().get_accounts()

	# test merge user

	def merge_users(self):
		utils.merge_user(self.user1.key, self.user2.key)

	def test_leave_group(self):
		""" Tests that merged users are removed from all groups """
		group = models.Group(
			assignment=self._assign.key,
			member=[self.user1.key, self.user2.key, self.user3.key])
		group.put()
		self.merge_users()
		group = models.Group.query(models.Group.assignment==self._assign.key).get()
		self.assertEqual(group.member, [self.user1.key, self.user3.key])

	def test_copy_submissions(self):
		""" Tests that all submissions are copied to the new user successfully """
		query1 = models.FinalSubmission.query(models.FinalSubmission.submitter==self.user1.key)
		query2 = models.FinalSubmission.query(models.FinalSubmission.submitter==self.user2.key)
		self.assertEqual([], list(query1.fetch()))
		self.assertNotEqual([], list(query2.fetch()))
		self.merge_users()
		self.assertNotEqual([], list(query1.fetch()))  # user1 receives user2 subs
		self.assertEqual([], list(query2.fetch()))  # user2 is no longe the owner

	# def test_deactivate_enrollment(self):
	# 	""" Tests that the merged user has been unenrolled from all courses """
	# 	part1 = models.Participant(
	# 		course=self._course.key,
	# 		role='student',
	# 		user=self.user1.key
	# 	).put()
	# 	models.Participant(
	# 		course=self._course.key,
	# 		role='student',
	# 		user=self.user2.key
	# 	).put()
	# 	self.merge_users()
	# 	self.assertEqual([part1.get()], self._course.get_students(self.user))

	def test_emails_transferred(self):
		""" Tests that emails have been merged in. """
		self.assertEqual(['dummy2@student.com'], self.user2.email)
		self.assertEqual(['dummy@student.com'], self.user1.email)
		self.merge_users()
		self.assertEqual(['#dummy2@student.com'], self.user2.key.get().email)
		self.assertEqual(['dummy@student.com', 'dummy2@student.com'], self.user1.key.get().email)

	# def test_user_status(self):
	# 	""" Tests that the old user has been deactivated. """
	# 	self.assertEqual('active', self.user2.status)
	# 	self.assertEqual('active', self.user1.status)
	# 	self.merge_users()
	# 	self.assertEqual('inactive', self.user2.key.get().status)
	# 	self.assertEqual('active', self.user1.key.get().status)