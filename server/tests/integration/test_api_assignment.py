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
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission, make_fake_group #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils
from ddt import ddt, data, unpack
from app.exceptions import *
from integration.test_api_base import APITest


class AssignmentAPITest(APIBaseTestCase):
	model = models.Assignment
	API = api.AssignmentAPI
	name = 'assignment'
	num = 1
	access_token = 'dummy_admin'

	def setUp(self):
		super(AssignmentAPITest, self).setUp()
		self.user = self.accounts['dummy_admin']
		self.user1 = self.accounts['dummy_student']
		self.user2 = self.accounts['dummy_student2']
		self.user3 = self.accounts['dummy_student3']
		self.assignment_name = 'Hog Project'
		self._course = make_fake_course(self.user)
		self._course.put()
		self._assign = make_fake_assignment(self._course, self.user)
		self._assign.autograding_enabled = True
		self._assign.autograding_key = "NotReallyAnAutograderKey"
		self._assign.name = self._assign.display_name = self.assignment_name
		self._assign.put()
		self._group = make_fake_group(self._assign, self.user1, self.user2)
		self._backup = make_fake_backup(self._assign, self.user2)
		self._submission = make_fake_submission(self._backup)
		self._finalsubmission = make_fake_finalsubmission(self._submission, self._assign, self.user2)

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

	def get_accounts(self):
		return APITest().get_accounts()

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
		""" Test that error thrown when course does not exist """
		with self.assertRaises(BadValueError):
			self.API().post(self.accounts['dummy_admin'], {
				'creator': self.accounts['dummy_admin'].key,
				'course': ndb.Key(models.Course, self._course.key.id() + 1)
			})

	def test_post_duplicate(self):
		""" Post duplicate entity """
		with self.assertRaises(BadValueError):
			self.API().post(self.accounts['dummy_admin'], {
				'name': self.assignment_name,
				'course': self._course.key
			})

	def test_post_nondupliacte(self):
		""" Tests successful post """
		self.API().post(self.accounts['dummy_admin'], {
			'name': 'New Homework',
		    'course': self._course.key
		})
		self.assertIsNot(None, models.Assignment.query(models.Assignment.name == 'New Homework').get())

	def test_edit(self):
		""" Tests that edit works """
		self.API().edit(self._assign, self.accounts['dummy_admin'], {
			'name': self.assignment_name,
		    'url': 'okpy.org',
		    'course': self._course.key
		})
		self.assertEqual('okpy.org', self._assign.key.get().url)

	def test_assign(self):
		""" Tests that assign functions without dying """
		self.API().assign(self.accounts['dummy_admin'], self.accounts['dummy_admin'], {})

	def test_assign_check(self):
		""" Tests that assign checks for permissions  """
		with self.assertRaises(PermissionError):
			self.API().assign(self.accounts['dummy_student3'], self.accounts['dummy_student2'], {})

	def test_invite_err(self):
		""" Test that error is thrown if need be"""
		self.mock(models.Group, 'invite_to_group').using(lambda *args: True)
		with self.assertRaises(BadValueError):
			group_wrapper = self.obj().set(key=self._group)
			self.API().invite(self.accounts['dummy_admin'], group_wrapper, {
				'email': 'dummy@admin.com'
			})

	def test_download_scores_check(self):
		""" Tests that download_scores checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().download_scores(self._assign, self.accounts['dummy_student3'], {})

	def test_download_scores_basic(self):
		""" Tests that admin allowed to download scores """
		self.API().download_scores(self._assign, self.accounts['dummy_admin'], {})

	def test_statistics_check(self):
		""" Tests that stats permissions checked """
		with self.assertRaises(PermissionError):
			self.API().statistics(self._assign,
				self.accounts['dummy_student3'], {})

	def test_statistics_basic(self):
		""" Tests that stats will be downloaded """
		self.API().statistics(self._assign, self.accounts['dummy_admin'], {})

	def test_autograde_check(self):
		""" Tests that autograde has permissions check """
		with self.assertRaises(PermissionError):
			self.API().autograde(self._assign, self.accounts['dummy_student3'], {})

	def test_autograde_notenabled(self):
		""" Tests if autograding not enabled """
		with self.assertRaises(BadValueError):
			self._assign.autograding_enabled = False
			self.API().autograde(self._assign, self.accounts['dummy_admin'], {})

	def test_autograde_if_check(self):
		""" Tests if autograding checks for grade_final """
		with self.assertRaises(BadValueError):
			self.API().autograde(self._assign, self.accounts['dummy_admin'],
				{'grade_final': False})

	def test_autograde_key_check(self):
		""" Tests if autograding checks for autograding_key """
		with self.assertRaises(BadValueError):
			self._assign.autograding_key = None
			self.API().autograde(self._assign, self.accounts['dummy_admin'],
				{'grade_final': False})

	def test_autograde_rejected_request(self):
		""" Tests report for autograding failure """
		with self.assertRaises(BadValueError):
			import requests
			self.mock(requests, 'post').using(lambda *args, **kwargs: self.obj().set(status_code=900))
			# Use the deferred task - since that's where submission occurs.
			utils.autograde_final_subs(self._assign, self.accounts['dummy_admin'], {
				'grade_final': True,
				'token': 'gibberish'
			})

	def test_autograde_successful_request_basic(self):
		""" Tests successful autograding just runs - does not check for functioanlity """
		import requests
		self.mock(requests, 'post').using(lambda *args, **kwargs: self.obj().set(status_code=200))
		utils.autograde_final_subs(self._assign, self.accounts['dummy_admin'], {
			'grade_final': True,
			'token': 'gibberish'
		})

	def test_queues_check(self):
		""" Tests that queues checked """
		with self.assertRaises(PermissionError):
			self.API().queues(self._assign, self.accounts['dummy_student3'], {})

	def test_queues_result_basic(self):
		""" Tests that result has results """
		models.Queue(assignment=self._assign.key).put()
		self.assertEqual(
			len(self.API().queues(self._assign, self.accounts['dummy_admin'], {})),
			1)
