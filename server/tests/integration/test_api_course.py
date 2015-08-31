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

	def test_course_index(self):
		""" Test that onlyenrolled takes effect """
		results = self.API().index(self.accounts['dummy_admin'], {
			'onlyenrolled': True
		})['results']
		self.assertEqual(0, len(results))

	def test_add_staff_permission(self):
		""" Tests that add_staff checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().add_staff(self._course, self.accounts['dummy_student3'], {})

	def test_add_staff_normal(self):
		""" Tests that user is added as staff """
		self.API().add_staff(self._course, self.accounts['dummy_admin'], {
			'email': self.accounts['dummy_student3'].email[0]
		})
		part = models.Participant.query(models.Participant.user == self.accounts['dummy_student3'].key).get()
		self.assertNotEqual(None, part)

	def test_get_staff_permissions(self):
		""" Tests that get_staff checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().get_staff(self._course, self.accounts['dummy_student3'], {})

	def test_get_staff_works(self):
		""" Tests that get_staff returns some kind of list, filled only with staff members """
		staff = self.API().get_staff(self._course, self.accounts['dummy_admin'], {})
		self.assertTrue(isinstance(staff, list))
		for member in staff:
			self.assertTrue(isinstance(member, models.Participant))
			self.assertEqual(member.role, constants.STAFF_ROLE)

	def test_remove_staff_permissions(self):
		""" Tests that remove_staff checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().remove_staff(self._course, self.accounts['dummy_student3'], {})

	def test_remove_staff_existent(self):
		""" Tests that existent member is removed """
		self.API().remove_staff(self._course, self.accounts['dummy_admin'], {
			'email': self.accounts['dummy_student3'].email[0]
		})

	def test_remove_staff_nonexistent(self):
		""" Tests that nonexistent member reports error """
		with self.assertRaises(BadValueError):
			self.API().remove_staff(self._course, self.accounts['dummy_admin'], {
				'email': 'wh@tever.com'
			})

	def test_get_students_permissions(self):
		""" Tests that get_students checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().get_students(self._course, self.accounts['dummy_student3'], {})

	def test_get_students_works(self):
		""" Tests that get_students returns some kind of list, filled only with students """
		staff = self.API().get_students(self._course, self.accounts['dummy_admin'], {})
		self.assertTrue(isinstance(staff, list))
		for member in staff:
			self.assertTrue(isinstance(member, models.Participant))
			self.assertEqual(member.role, constants.STUDENT_ROLE)

	def test_add_students_permissions(self):
		""" Tests that add_students checks for permissions """
		with self.assertRaises(PermissionError):
			self.API().add_students(self._course, self.accounts['dummy_student3'], {})

	def test_add_students_results(self):
		""" Tests that add_students functions """
		roster_old = self.API().get_students(self._course, self.accounts['dummy_admin'], {})
		self.API().add_students(self._course, self.accounts['dummy_admin'], {
			'emails': [
				self.accounts['dummy_student3'].email[0],
				self.accounts['dummy_student2'].email[0]
			]
		})
		roster_new = self.API().get_students(self._course, self.accounts['dummy_admin'], {})
		self.assertTrue(len(roster_new) > len(roster_old))

	def test_add_student_permission(self):
		""" Tests that add_student checks permissions """
		with self.assertRaises(PermissionError):
			self.API().add_student(self._course, self.accounts['dummy_student3'], {})

	def test_add_student_results(self):
		""" Tests that add_students functions """
		roster_old = self.API().get_students(self._course, self.accounts['dummy_admin'], {})
		self.API().add_student(self._course, self.accounts['dummy_admin'], {
			'email': self.accounts['dummy_student3'].email[0]
		})
		roster_new = self.API().get_students(self._course, self.accounts['dummy_admin'], {})
		self.assertEqual(len(roster_new) - 1, len(roster_old))

	def test_remove_student_permission(self):
		""" Tests that remove_student checks permissions """
		with self.assertRaises(PermissionError):
			self.API().remove_student(self._course, self.accounts['dummy_student3'], {})

	def test_remove_student_results(self):
		""" Tests taht tudents are actually removed """
		self.API().add_students(self._course, self.accounts['dummy_admin'], {
			'emails': [
				self.accounts['dummy_student3'].email[0],
				self.accounts['dummy_student2'].email[0]
			]
		})
		roster_old = self.API().get_students(self._course, self.accounts['dummy_admin'], {})
		self.API().remove_student(self._course, self.accounts['dummy_admin'], {
			'email': self.accounts['dummy_student3'].email[0]
		})
		roster_new = self.API().get_students(self._course, self.accounts['dummy_admin'], {})
		self.assertEqual(len(roster_new) + 1, len(roster_old))

	def test_remove_student_nonexistnet(self):
		""" Tests that a nonexistent student is checked """
		with self.assertRaises(BadValueError):
			self.API().remove_student(self._course, self.accounts['dummy_admin'], {
				'email': 'wh@tever.com'
			})

	def test_assignments(self):
		""" Tests that get_assignments fetches assignments """
		assignments = self.API().assignments(self._course, None, {})
		self.assertTrue(isinstance(assignments, list))
		for assignment in assignments:
			self.assertTrue(isinstance(assignment, models.Assignment))
