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
from app import models, constants, utils, api
from ddt import ddt, data, unpack
from app.exceptions import *
from integration.test_api_base import APITest


class CourseAPITest(APITest, APIBaseTestCase):
	model = models.Course
	API = api.CourseAPI
	name = 'course'
	num = 1
	access_token = 'dummy_admin'

	def get_basic_instance(self, mutate=True):
		name = 'testcourse'
		if mutate:
			name += str(self.num)
			self.num += 1
		rval = make_fake_course(self.user)
		rval.name = name
		return rval

	def setUp(self):
		super(CourseAPITest, self).setUp()
		self.user = self.accounts['dummy_admin']
		self.user1 = self.accounts['dummy_student']
		self.user2 = self.accounts['dummy_student2']
		self.user3 = self.accounts['dummy_student3']
		self.assignment_name = 'Hog Project'
		self._course = self.get_basic_instance()
		self._assign = make_fake_assignment(self._course, self.user)
		self._assign.name = self._assign.display_name = self.assignment_name
		self._assign.put()
		self._backup = make_fake_backup(self._assign, self.user2)
		self._submission = make_fake_submission(self._backup)
		self._version = self.get_basic_instance()

	def get_accounts(self):
		return APITest().get_accounts()
	
	# def test_course_index(self):
	# 	""" Test that onlyenrolled takes effect """
	# 	results = self.API().index(self.accounts['dummy_admin'], {
	# 		'onlyenrolled': True
	# 	})['results']
	# 	self.assertEqual(0, len(results))
	#
	# def test_add_staff_permission(self):
	# 	""" Tests that add_staff checks for permissions """
	#