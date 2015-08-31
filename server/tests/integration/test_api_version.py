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
import flask
from test_base import APIBaseTestCase, unittest, api, mock #pylint: disable=relative-import
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils, api
from ddt import ddt, data, unpack
from app.exceptions import *
from integration.test_api_base import APITest


class VersionAPITest(APITest, APIBaseTestCase):
	model = models.Version
	API = api.VersionAPI
	name = 'version'
	num = 1
	access_token = 'dummy_admin'

	def get_basic_instance(self, mutate=True):
		name = 'testversion'
		if mutate:
			name += str(self.num)
			self.num += 1
		return self.model(key=ndb.Key(self.model._get_kind(), name),
		                  name=name, versions=['1.0.0', '1.1.0'], base_url="https://www.baseurl.com")

	def setUp(self):
		super(VersionAPITest, self).setUp()
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
		self._version = self.get_basic_instance()

	def get_accounts(self):
		return APITest().get_accounts()

	def test_new_permission(self):
		""" Test that new checks for permisions """
		with self.assertRaises(PermissionError):
			self.API().new(self._version, self.accounts['dummy_student3'], {})

	def test_new_duplicate(self):
		""" Test that duplicate versions not allowed """
		with self.assertRaises(BadValueError):
			self.API().new(self._version, self.accounts['dummy_admin'], {
				'version': '1.0.0'
			})

	def test_new_current(self):
		""" Test that the current_Version can be/is set """
		obj = self.API().new(self._version, self.accounts['dummy_admin'], {
			'version': '1.1.1',
		    'current': '1.1.1'
		})
		self.assertEqual(obj.current_version, '1.1.1')

	def test_current_permission(self):
		""" Tests that current checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().current(self.never_can(), self.accounts['dummy_student3'], {})

	def test_current_invalid_version(self):
		""" Tests that lack of current_version is caught """
		with self.assertRaises(BadValueError):
			self.API().current(self._version, self.accounts['dummy_admin'], {})

	def test_current_normal(self):
		""" Tests that current_Version is returned """
		self._version.current_version = '9.0'
		cv = self.API().current(self._version, self.accounts['dummy_admin'], {})
		self.assertEqual(cv, '9.0')

	def test_download_permissions(self):
		""" Tests that download checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().download(self.never_can(), self.accounts['dummy_student3'], {})

	@mock(flask, 'redirect', lambda x: x)
	def test_download_link_without_version(self):
		""" Tests that download link without version is acceptable """
		self._version.current_version = '1.0.0'
		self._version.put()
		self.API().download(self._version, self.accounts['dummy_admin'], {})

	@mock(flask, 'redirect', lambda x: x)
	def test_download_link_with_version(self):
		""" Tests that download link with version is acceptable """
		dl = self.API().download(self._version, self.accounts['dummy_admin'], {'version': '1.0.0'})
		self.assertIn('1.0.0', dl)

	@mock(flask, 'redirect', lambda x: x)
	def test_download_link_with_version(self):
		""" Tests that invalid version is not acceptable """
		with self.assertRaises(BadValueError):
			dl = self.API().download(self._version, self.accounts['dummy_admin'], {'version': '8.9.0'})
			self.assertIn('8.9.0', dl)

	def test_set_current_permission(self):
		""" Tests that set_current checks permissions """
		with self.assertRaises(PermissionError):
			self.API().set_current(self.never_can(), self.accounts['dummy_student3'], {})

	def test_set_current_invalid_Version(self):
		""" Tests that nonexistent version is caught """
		with self.assertRaises(BadValueError):
			self.API().set_current(self._version, self.accounts['dummy_admin'], {
				'version': '9.0.0'
			})

	def test_set_current_normal(self):
		""" Tests that set_current functions properly, verifies behavior """
		self._version.current_version = '1.1.0'
		self._version.put()
		self.API().set_current(self._version, self.accounts['dummy_admin'], {
			'version': '1.1.0'
		})
		self._version = self._version.key.get()
		self.assertEqual(self._version.current_version, '1.1.0')
