#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=invalid-name, import-error

"""
Tests for the analytics framework
"""

import os
import time
os.environ['FLASK_CONF'] = 'TEST'
from test_permissions import BaseUnitTest
from google.appengine.ext import deferred
from integration.test_api_base import APITest
from test_base import mock

from app import models
from app.analytics import Job
from app.analytics.job import AnalyticsDump
from app.analytics.jobs import sample_job


def simple_mapper(entity):
    return 1


def error_mapper(entity):
    return 1 / 0


def error_reducer(map_result):
    return 1 / 0


def simple_reducer(map_result):
    return len(map_result)


class BasicJobTest(BaseUnitTest):

    def generate_simple_job(self, kind, map_error=False, reduce_error=False):
        mapper = error_mapper if map_error else simple_mapper
        reducer = error_reducer if reduce_error else simple_reducer
        return Job(kind, self.get_accounts()['admin'], mapper, reducer, [])

    def run_job(self, job):
        job.start()
        tasks = self.taskqueue_stub.get_filtered_tasks()
        self.assertEqual(1, len(tasks))
        task = tasks[0]
        deferred.run(task.payload)

    def test_run_simple_user_job(self):
        j = self.generate_simple_job(models.User)
        self.run_job(j)
        j.wait()
        dump = j.get_dump()
        self.assertEqual(j.SUCCESS, dump.status)
        self.assertEqual(len(self.get_accounts()), dump.result['result'])

    def test_job_map_error(self):
        j = self.generate_simple_job(models.User, map_error=True)
        try:
            self.run_job(j)
        except deferred.PermanentTaskFailure:
            pass
        j.wait()
        dump = j.get_dump()
        self.assertEqual(j.FAILURE, dump.status)

    def test_job_reduce_error(self):
        j = self.generate_simple_job(models.User, reduce_error=True)
        try:
            self.run_job(j)
        except deferred.PermanentTaskFailure:
            pass
        j.wait()
        dump = j.get_dump()
        self.assertEqual(j.FAILURE, dump.status)

    @mock(time, 'sleep', lambda s: '')
    def test_wait(self):
        """ Tests that wait works """
        self.mock(Job, '__init__').using(object.__init__)
        data, job = dict(i=0), Job()

        def get_status():
            data['i'] += 1  # hack for nonlocal, tests run in Python2
            if data['i'] >= 10:
                return job.FAILURE
            return 'yolo'
        job.get_status = get_status
        job.wait()

    def test_permissions_index(self):
        """ Tests that only admin can index"""
        need = self.obj().set(action='index')
        student, admin = self.get_accounts()['student0'], self.get_accounts()['admin']
        self.assertTrue(AnalyticsDump._can(student, need, None, self.obj().set(filter=lambda *args: True)))
        self.assertTrue(AnalyticsDump._can(admin, need, None, True))

    def test_permission_get(self):
        """ Tests that only object owners and admin can get """
        need = self.obj().set(action='get')
        student, admin = self.get_accounts()['student0'], self.get_accounts()['admin']
        self.assertTrue(AnalyticsDump._can(student, need, self.obj().set(owner=student.key), None))
        self.assertTrue(AnalyticsDump._can(admin, need, None, None))

    def test_permission_rogue_method(self):
        """ Tests that rogue method gives false """
        need = self.obj().set(action='put')
        admin = self.get_accounts()['admin']
        self.assertFalse(AnalyticsDump._can(admin, need, None, None))

    def test_job_email(self):
        user = self.get_accounts()['student0']
        self.assertEqual(user.email, sample_job.mapper(user))

    def test_job_reducer(self):
        self.assertEqual(2, sample_job.reducer([1, 2]))
