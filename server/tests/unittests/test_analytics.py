#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=invalid-name, import-error

"""
Tests for the analytics framework
"""

import os
os.environ['FLASK_CONF'] = 'TEST'
from test_permissions import BaseUnitTest
from google.appengine.ext import deferred


from app import models
from app.analytics import Job

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
