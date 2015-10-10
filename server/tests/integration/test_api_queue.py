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
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission, make_fake_queue #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils, api
from ddt import ddt, data, unpack
from app.exceptions import *
from integration.test_api_base import APITest


class QueueAPITest(APIBaseTestCase):
    model = models.Queue
    API = api.QueueAPI
    name = 'queue'

    def setUp(self):
        super(QueueAPITest, self).setUp()
        self.user = self.accounts['dummy_admin']
        self.staff = self.accounts['dummy_staff']
        self.user1 = self.accounts['dummy_student']
        self.user2 = self.accounts['dummy_student2']
        self.user3 = self.accounts['dummy_student3']
        self.assignment_name = 'Hog Project'
        self._course = make_fake_course(self.user)
        self._course.put()
        self._assign = make_fake_assignment(self._course, self.user)
        self._assign.name = self._assign.display_name = self.assignment_name
        self._assign.put()

    def get_accounts(self):
        return APITest().get_accounts()

    def get_basic_instance(self, mutate=True):
        return make_fake_queue(self._assign, self.accounts['dummy_admin'])

    def test_new_entity_basic(self):
        """ Tests that new_entity works """
        self.API().new_entity({'assigned_staff': [self.accounts['dummy_admin'].key]})
        self.API().new_entity({
            'owner': self.accounts['dummy_admin'].key,
            'assigned_staff': [self.accounts['dummy_admin'].key]
        })

    def test_get_instance_basic(self):
        """ Tests that get queue works """
        queue = self.get_basic_instance()
        res = self.API().get_instance(queue.key.id(), self.user)
        self.assertEqual(res, queue)

    def test_get_basic(self):
        """ Tests that get queue works """
        queue = self.get_basic_instance()
        res = self.API().get(queue, self.user, None)
        self.assertEqual(res, queue)

    def test_get_fields(self):
        """ Tests that get queue to_json gives us the expected fields """
        queue = self.get_basic_instance()
        queue.put()
        res = self.API().get(queue, self.user, None)
        data = res.to_json()
        keys =  ['count', 'graded', 'owner', 'assignment', 'id', 'submissions', 'remaining', 'assigned_staff']
        for key in keys:
            self.assertIn(key, data.keys())
