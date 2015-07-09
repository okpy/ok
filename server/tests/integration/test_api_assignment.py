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


class AssignmentAPITest(APITest, APIBaseTestCase):
	model = models.Assignment
	name = 'assignment'
	num = 1
	access_token = 'dummy_admin'

	def setUp(self):
		super(AssignmentAPITest, self).setUp()

	def get_basic_instance(self, mutate=True):
		name = 'proj'
		if mutate:
			name += str(self.num)
			self.num += 1

		self._course = make_fake_course(self.user)
		self._course.put()
		self.enroll_accounts(self._course)
		self._assignment = make_fake_assignment(self._course, self.user)
		self._assignment.name = name
		return self._assignment

	def post_entity(self, inst, *args, **kwds):
		"""Posts an entity to the server."""
		data = inst
		if not isinstance(data, dict):
			data = inst.to_json()
			data['course'] = data['course']['id']

		self.post_json('/{}'.format(self.name),
		               data=data, *args, **kwds)
		if self.response_json and 'key' in self.response_json:
			if inst.key:
				self.assertEqual(inst.key.id(), self.response_json['key'])
			else:
				inst.key = models.ndb.Key(self.model,
				                          self.response_json.get('key'))

	def test_course_does_not_exist(self):
		inst = self.get_basic_instance()
		data = inst.to_json()
		data['course'] = self._course.key.id() + 100000

		self.post_entity(data)

		self.assertStatusCode(400)