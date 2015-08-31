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
from test_base import APIBaseTestCase, unittest, BaseTestCase, mock #pylint: disable=relative-import
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils, api
from ddt import ddt, data, unpack
from app.exceptions import *
from integration.test_api_base import APITest


class AnalyticsAPITest(APIBaseTestCase):

	API = api.AnalyticsAPI

	def setUp(self):
		super(AnalyticsAPITest, self).setUp()
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

	def test_post_permissions(self):
		""" Test that post cehcks for permissions """
		with self.assertRaises(PermissionError):
			self.mock(api.AnalyticsAPI, 'model').using(BaseTestCase.never_can())
			self.API().post(self.accounts['dummy_student3'], None)

	def test_post_bad_filters(self):
		""" Test bad filters """
		with self.assertRaises(BadValueError):
			self.API().post(self.accounts['dummy_admin'], {
				'job_type': 'toilet-cleaning',
				'filters': 'uh oh'
			})

	def test_post_bad_filters_triples(self):
		""" Test bad filters that aren't triples """
		with self.assertRaises(BadValueError):
			self.API().post(self.accounts['dummy_admin'], {
				'job_type': 'toilet-cleaning',
				'filters': ['uh', 'oh']
			})

	def test_post_not_available_job(self):
		""" Tests that invalid job raises error """
		with self.assertRaises(BadValueError):
			self.API().post(self.accounts['dummy_admin'], {
				'job_type': 'toilet-cleaning',
				'filters': [('uh', 'oh', 'yikes')]
			})

	def test_post_normal(self):
		""" Test that an analytics job can be passed normally """
		status_code, message, data = self.API().post(self.accounts['dummy_admin'], {
			'job_type': 'sample',
			'filters': []
		})
		self.assertEqual(status_code, 201)
