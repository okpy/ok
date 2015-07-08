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


class CourseAPITest(APITest, APIBaseTestCase):
	model = models.Course
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