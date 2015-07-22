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


# class AssignmentAPITest(APITest, APIBaseTestCase):
# 	model = models.Assignment
# 	API = api.AssignmentAPI
# 	name = 'assignment'
# 	num = 1
# 	access_token = 'dummy_admin'
#
# 	def setUp(self):
# 		super(AssignmentAPITest, self).setUp()
# 		self.user = self.accounts['dummy_admin']
# 		self.user1 = self.accounts['dummy_student']
# 		self.user2 = self.accounts['dummy_student2']
# 		self.user3 = self.accounts['dummy_student3']
# 		self.assignment_name = 'Hog Project'
# 		self._course = make_fake_course(self.user)
# 		self._course.put()
# 		self._assign = make_fake_assignment(self._course, self.user)
# 		self._assign.name = self._assign.display_name = self.assignment_name
# 		self._assign.put()
# 		self._backup = make_fake_backup(self._assign, self.user2)
# 		self._submission = make_fake_submission(self._backup)
# 		self._finalsubmission = make_fake_finalsubmission(self._submission, self._assign, self.user2)
#
# 	def get_basic_instance(self, mutate=True):
# 		name = 'proj'
# 		if mutate:
# 			name += str(self.num)
# 			self.num += 1
#
# 		self._course = make_fake_course(self.user)
# 		self._course.put()
# 		self.enroll_accounts(self._course)
# 		self._assignment = make_fake_assignment(self._course, self.user)
# 		self._assignment.name = name
# 		return self._assignment
#
# 	def get_accounts(self):
# 		return APITest().get_accounts()
#
# 	def post_entity(self, inst, *args, **kwds):
# 		"""Posts an entity to the server."""
# 		data = inst
# 		if not isinstance(data, dict):
# 			data = inst.to_json()
# 			data['course'] = data['course']['id']
#
# 		self.post_json('/{}'.format(self.name),
# 		               data=data, *args, **kwds)
# 		if self.response_json and 'key' in self.response_json:
# 			if inst.key:
# 				self.assertEqual(inst.key.id(), self.response_json['key'])
# 			else:
# 				inst.key = models.ndb.Key(self.model,
# 				                          self.response_json.get('key'))
#
# 	def test_course_does_not_exist(self):
# 		inst = self.get_basic_instance()
# 		data = inst.to_json()
# 		data['course'] = self._course.key.id() + 100000
#
# 		self.post_entity(data)
#
# 		self.assertStatusCode(400)
#
# 	def test_post_duplicate(self):
# 		""" Post duplicate entity """
# 		with self.assertRaises(BadValueError):
# 			self.API().post(self.accounts['admin'], {'name': self.assignment_name})
#
# 	def test_edit(self):
# 		""" Tests that edit works """
# 		self.API().post(self._assign, self.accounts['admin'], {
# 			'name': self.assignment_name,
# 		    'url': 'okpy.org'
# 		})
# 		self.assertEqual('okpy.org', self._assign.key.get().url)
#
# 	def test_assign(self):
# 		""" Tests that assign functions without dying """
# 		self.API().assign(self.accounts['admin'], self.accounts['admin'], {})
#
# 	def test_assign_check(self):
# 		""" Tests that assign checks for permissions  """
# 		with self.assertRaises(PermissionError):
# 			self.API().assign(self.accounts['dummy_student3'], self.accounts['dummy_student2'], {})
#
# 	def test_invite_err(self):
# 		""" Test that error is thrown if need be"""
#