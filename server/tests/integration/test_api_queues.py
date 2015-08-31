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


class QueuesAPITest(APIBaseTestCase):

	API = api.QueuesAPI

	def setUp(self):
		super(QueuesAPITest, self).setUp()
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

	def test_check_permissions(self):
		""" Tests that check_permissions works """
		self.assertTrue(
			self.API().check_permissions(
				self.accounts['dummy_student3'], {'course': self._course.key}))

	def test_generate_permissions(self):
		""" TEsts that generate checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().generate(
				self.accounts['dummy_student'], {'course': self._course.key})

	def test_generate_no_staff(self):
		""" Tests that generate errors without staff """
		with self.assertRaises(BadValueError):
			self.API().generate(self.accounts['dummy_admin'], {
				'course': self._course.key,
			    'assignment': self._assign.key,
			    'staff': [self.accounts['dummy_admin'].email[0]]
			})

	def test_generate_normal(self):
		""" Tests that generate functions normally """
		models.Participant.add_role(self.accounts['dummy_admin'], self._course.key, constants.STAFF_ROLE)
		self.API().generate(self.accounts['dummy_admin'], {
			'course': self._course.key,
			'assignment': self._assign.key,
			'staff': [self.accounts['dummy_admin'].email[0]]
		})
