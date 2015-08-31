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
import json
from test_api_base import APITest
from test_base import APIBaseTestCase, unittest #pylint: disable=relative-import
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils, api
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

	def test_enrollment_empty(self):
		""" Tests that enrollment data is empty for unenrolled student """
		with self.app.test_request_context('/enrollment?email=gibberish@admin.com'):
			self.assertEqual(self.API().enrollment(), '[]')

	def test_enrollment_json(self):
		""" Tests that response is valid JSON """
		with self.app.test_request_context('/enrollment?email=dummy3@student.com'):
			models.Participant.add_role(self.accounts['dummy_student3'], self._course, constants.STUDENT_ROLE)
			data = json.loads(self.API().enrollment())
			self.assertEqual(1, len(data))

	def test_enrollment_validity(self):
		""" Tests enrollment data is accurate """

		with self.app.test_request_context('/enrollment?email=dummy3@student.com'):
			models.Participant.add_role(self.accounts['dummy_student3'], self._course, constants.STUDENT_ROLE)
			data = json.loads(self.API().enrollment())
			self.assertEqual(1, len(data))

			datum = data[0]
			self.assertEqual(datum['display_name'], self._course.display_name)
			self.assertEqual(datum['institution'], self._course.institution)
			self.assertEqual(datum['offering'], self._course.offering)
			self.assertEqual(datum['url'], '/#/course/'+str(self._course.key.id()))

			self.assertEqual(datum['term'], 'fall')
			self.assertEqual(datum['year'], '2014')

			self._course.offering = 'summer/2015'
			self._course.put()

			datum = json.loads(self.API().enrollment())[0]

			self.assertEqual(datum['term'], None)
			self.assertEqual(datum['year'], None)

	def test_check(self):
		""" Test check functionality """
		models.Participant.add_role(self.accounts['dummy_student3'], self._course, constants.STUDENT_ROLE)
		models.Participant.add_role(self.accounts['dummy_student2'], self._course, constants.STUDENT_ROLE)
		self.API().check(['dummy2@student.com', 'dummy3@student.com'], self._course, constants.STUDENT_ROLE)

		with self.assertRaises(BadValueError):
			self.API().check(['dummy2@student.com', 'dummy3@student.com'], self._course, constants.STAFF_ROLE)
