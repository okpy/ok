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


class QueueAPITest(APIBaseTestCase):

	API = api.QueueAPI

	def setUp(self):
		super(QueueAPITest, self).setUp()

	def get_accounts(self):
		return APITest().get_accounts()

	def test_new_entity_basic(self):
		""" Tests that new_entity works """
		self.API().new_entity({'assigned_staff': [self.accounts['dummy_admin'].key]})
		self.API().new_entity({
			'owner': self.accounts['dummy_admin'].key,
			'assigned_staff': [self.accounts['dummy_admin'].key]
		})
