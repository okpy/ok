#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

import os
os.environ['FLASK_CONF'] = 'TEST'
import unittest
from test_permissions import PermissionsUnitTest

from ddt import ddt, data

PTest = PermissionsUnitTest.PTest
QUEUE_TESTS = [
    PTest("student_get_queue",
          "student0", "Queue", "first", "get", False),
]

#pylint: disable=no-init, missing-docstring
@ddt
class QueuePermissionsUnitTest(PermissionsUnitTest):
    @data(*QUEUE_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
    unittest.main()
