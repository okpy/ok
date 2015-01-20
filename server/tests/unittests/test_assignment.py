#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

#from test_base import unittest #pylint: disable=relative-import
import unittest
from test_permissions import PermissionsUnitTest

from ddt import ddt, data

PTest = PermissionsUnitTest.PTest
PERMISSIONS_TESTS = [
    PTest("student_get_assignment",
          "student0", "Assignment", "first", "get", True),
    PTest("anon_get_assignment",
          "anon", "Assignment", "first", "get", True),
    PTest("student_create_assignment",
          "student0", "Assignment", "first", "create", False),
    PTest("admin_create_assignment",
          "admin", "Assignment", "first", "create", True),
    PTest("anon_create_assignment",
          "anon", "Assignment", "first", "create", False),
    PTest("admin_delete_normal",
          "admin", "Assignment", "first", "delete", False),
    PTest("staff_delete_normal",
          "staff", "Assignment", "first", "delete", False),
    PTest("admin_delete_empty",
          "admin", "Assignment", "empty", "delete", False),
    PTest("staff_delete_empty",
          "staff", "Assignment", "empty", "delete", False),
    PTest("staff_delete_empty",
          "empty_staff", "Assignment", "empty", "delete", False),
]

#pylint: disable=no-init, missing-docstring
@ddt
class AssignmentPermissionsUnitTest(PermissionsUnitTest):
    @data(*PERMISSIONS_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
    unittest.main()
