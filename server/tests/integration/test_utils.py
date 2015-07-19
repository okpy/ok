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

from test_base import APIBaseTestCase
from test_base import utils
from integration.test_api_base import APITest
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import


class UtilsTestCase(APIBaseTestCase):

	def setUp(self):
		super(UtilsTestCase, self).setUp()
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
	
	def test_zip_filename_purified(self):
		""" Test that filename doesn't contain weird chars """
		user = lambda: '_'
		user.email = ['test@example.com']
		fn = utils.make_zip_filename(user)
		
		assert fn.split('.')[1] == 'zip'
		assert '@' not in fn
		assert ' ' not in fn
		
	def test_add_subm_to_zip(self):
		""" Test that submission contents added to zip """
		