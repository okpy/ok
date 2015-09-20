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
from test_base import APIBaseTestCase, unittest, TestingError #pylint: disable=relative-import
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils, api
from ddt import ddt, data, unpack
from app.exceptions import *
from integration.test_api_base import APITest


class UserAPITest(APIBaseTestCase):

	API = api.UserAPI

	def setUp(self):
		super(UserAPITest, self).setUp()
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

	def test_get(self):
		""" Tests that without 'course', user does not get_course_info """
		obj = self.obj().set(get_course_info=self.raise_error)
		self.API().get(obj, None, {})
		assert True  # no error triggered

	def test_get_with_course(self):
		""" Tests that with 'course', user triggers get_course_info """
		obj = self.obj().set(get_course_info=self.raise_error)
		with self.assertRaises(TestingError):
			self.API().get(obj, None, {'course': self._course.key})

	def test_get_instance(self):
		""" Tests for error if user does not exist """
		with self.assertRaises(BadKeyError):
			self.API().get_instance('gibberish@student.com', None)

	def test_get_instance_valid(self):
		""" Tests object if returned for valid instance """
		obj = api.UserAPI.model.lookup('dummy2@student.com')
		self.assertEqual(
			self.API().get_instance(
				'dummy2@student.com',
				self.accounts['dummy_admin']), obj)

	def test_get_instance_check_permissions(self):
		""" Tests that permissions are checked """
		with self.assertRaises(PermissionError):
			self.API().get_instance('dummy2@student.com', self.accounts['dummy_student3'])

	def test_new_entity(self):
		""" Tests that a new entity is created """
		ent = self.API().new_entity({'email': 'gibberish@student.com'})
		self.assertEqual(['gibberish@student.com'], ent.email)

	def test_new_entity_exists(self):
		""" Tests error if student already exists """
		with self.assertRaises(BadValueError):
			self.API().new_entity({'email': 'dummy@admin.com'})

	def test_add_email_check(self):
		""" Tests that add_email checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().add_email(
				self.accounts['dummy_admin'],
				self.accounts['dummy_student3'],
				None)

	def test_add_email_function(self):
		""" Tests that add_email actually adds the email """
		self.API().add_email(
			self.accounts['dummy_student3'],
			self.accounts['dummy_admin'],
			{'email': 'hoho@admin.com'})
		obj = self.API().get_instance('dummy3@student.com', self.accounts['dummy_admin'])
		self.assertIn('hoho@admin.com', obj.email)

	def test_delete_email_check(self):
		""" Tests that delete email checks permissions """
		with self.assertRaises(PermissionError):
			self.API().delete_email(
				self.accounts['dummy_admin'],
				self.accounts['dummy_student3'],
				None)

	def test_delete_email_function(self):
		""" Tests that delete email actually deletes the email """
		self.API().add_email(
			self.accounts['dummy_student3'],
			self.accounts['dummy_admin'],
			{'email': 'hoho@admin.com'})
		self.API().delete_email(
			self.accounts['dummy_student3'],
			self.accounts['dummy_admin'],
			{'email': 'hoho@admin.com'})
		obj = self.API().get_instance('dummy3@student.com', self.accounts['dummy_admin'])
		self.assertNotIn('hoho@admin.com', obj.email)

	def test_invitations_without_assignment(self):
		""" Verifies results of invitations, w/o assignment """
		user = self.accounts['dummy_student3']
		query = models.Group.query(models.Group.invited == user.key)
		self.assertEqual(self.API().invitations(user, user, {}), list(query))

	def test_invitations_with_assignment(self):
		""" Verifies results of invitations, w/o assignment """
		user = self.accounts['dummy_student3']
		query = models.Group.query(models.Group.invited == user.key).filter(models.Group.assignment==self._assign.key)
		self.assertEqual(self.API().invitations(user, user, {'assignment': self._assign.key}), list(query))

	def test_queues_basic(self):
		""" Test that fetching all queues works """
		queues = self.API().queues(None, self.accounts['dummy_admin'], None)
		self.assertTrue(isinstance(queues, list))

		for queue in queues:
			self.assertEqual(queue.assigned_staff, self.accounts['dummy_admin'].key)

	def test_create_staff_permissions(self):
		""" Tests that create_Staff checks for permissions """
		admin, user = self.accounts['dummy_admin'], self.accounts['dummy_student3']
		with self.assertRaises(PermissionError):
			self.API().create_staff(user, user, {})

	def test_create_staff_function(self):
		""" Tests that staff is actually added """
		admin, user = self.accounts['dummy_admin'], self.accounts['dummy_student3']
		models.Participant.add_role(admin, self._course, constants.STAFF_ROLE)
		self.API().create_staff(user, admin, {
			'role': constants.STAFF_ROLE,
			'email': self.obj().set(id=lambda: 'dummy3@student.com')
		})
		self.assertEqual(1, len(models.Participant.query(models.Participant.course == self._course.key).fetch()))
		self.assertEqual(models.User.query(models.User.email==self.user3.email[0]).get().role, constants.STAFF_ROLE)

	def test_get_fsubm(self):
		""" Tests vaildity of fetched final submission """
		user = self.user2
		fsubm = self.API().final_submission(user, user, {'assignment': self._assign.key})
		self.assertEqual(fsubm.submitter, user.key)
		self.assertEqual(fsubm.assignment, self._assign.key)
		self.assertTrue(isinstance(fsubm, models.FinalSubmission))

	def test_get_backups(self):
		""" Tests validity of fetched backups """
		backups = self.API().get_backups(self.user2, None, {
			'assignment': self._assign.key,
			'quantity': 5
		})
		self.assertEqual(len(backups), 1)

	def test_get_submissions(self):
		""" Test get submissions """
		subms = self.API().get_submissions(self.user2, None, {
			'assignment': self._assign.key,
			'quantity': 5
		})
		self.assertEqual(len(subms), 1)

		for subm in subms:
			self.assertTrue(isinstance(subm, models.Submission))

	def test_merge_user_permissions(self):
		""" Tests that merge user checks permissions """
		with self.assertRaises(PermissionError):
			self.API().merge_user(self.user1, self.user2, {})

	def test_merge_user_nonexistent_user(self):
		""" Tests that merge user throws error with invalid user """
		with self.assertRaises(BadValueError):
			self.API().merge_user(self.user2, self.user, {
				'other_email': 'invalid@dummy.com'
			})

	def test_merge_user_ok(self):
		""" Tests that merge user does not die """
		self.API().merge_user(self.user2, self.user, dict(other_email='dummy3@student.com'))
