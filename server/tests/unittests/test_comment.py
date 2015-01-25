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
PERMISSIONS_TESTS = [
    PTest("student_get_comment",
          "student0", "Comment", "first", "get", True),
]

#pylint: disable=no-init, missing-docstring
@ddt
class AssignmentPermissionsUnitTest(PermissionsUnitTest):
    @data(*PERMISSIONS_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
    unittest.main()
