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