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


class BackupAPITest(APITest, APIBaseTestCase):
	model = models.Backup
	name = 'submission'
	access_token = "submitter"

	num = 1
	def setUp(self):
		super(BackupAPITest, self).setUp()
		self.assignment_name = u'test assignment'
		self._course = make_fake_course(self.user)
		self._course.put()
		self._assign = make_fake_assignment(self._course, self.user)
		self._assign.name = self.assignment_name
		self._assign.put()

		self._submitter = self.accounts['dummy_student']
		self._submitter.put()
		self.logout()
		self.login('dummy_student')

	def get_basic_instance(self, mutate=True):
		rval = models.Backup(
			submitter=self._submitter.key,
			assignment=self._assign.key)
		return rval

	def post_entity(self, inst, *args, **kwds):
		"""Posts an entity to the server."""
		data = inst.to_json()
		data['assignment'] = self.assignment_name
		data['submitter'] = data['submitter']['id']

		self.post_json('/{}'.format(self.name),
		               data=data, *args, **kwds)
		if self.response_json and 'key' in self.response_json:
			if inst.key:
				self.assertEqual(inst.key.id(), self.response_json['key'])
			else:
				inst.key = models.ndb.Key(self.model,
				                          self.response_json.get('key'))

	def test_invalid_assignment_name(self):
		self.assignment_name = 'assignment'
		inst = self.get_basic_instance()

		self.post_entity(inst)
		self.assertStatusCode(400)

	def test_sorting(self):
		time = datetime.datetime.now()
		delta = datetime.timedelta(days=1)
		changed_time = time - delta

		inst = self.get_basic_instance()
		inst.created = changed_time
		inst.put()

		inst2 = self.get_basic_instance(mutate=True)
		inst2.created = time
		inst2.put()

		self.get_index(created='>|%s' % str(changed_time - datetime.timedelta(hours=7)))
		self.assertJson([inst2.to_json()])

		self.get_index(created='<|%s' % str(time - datetime.timedelta(hours=7)))
		self.assertJson([inst.to_json()])
