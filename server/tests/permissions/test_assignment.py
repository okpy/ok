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
    PTest("student_get_assignment",
          "student0", "Assignment", "first", "get", True),
    PTest("student_grade_assignment",
          "student0", "Assignment", "first", "grade", False),
    PTest("anon_get_assignment",
          "anon", "Assignment", "first", "get", True),
    PTest("student_create_assignment",
          "student0", "Assignment", "first", "create", False),
    PTest("student_staff_assignment",
          "student0", "Assignment", "first", "staff", False),
    PTest("admin_create_assignment",
          "admin", "Assignment", "first", "create", True),
    PTest("anon_create_assignment",
          "anon", "Assignment", "first", "create", False),
    PTest("anon_edit_assignment",
          "anon", "Assignment", "first", "put", False),
    PTest("anon_delete_assignment",
          "anon", "Assignment", "first", "delete", False),
    PTest("anon_grade_assignment",
          "anon", "Assignment", "first", "grade", False),
    PTest("anon_staff_assignment",
          "anon", "Assignment", "first", "staff", False),
    PTest("staff_edit_assignment",
          "staff", "Assignment", "first", "put", True),
    PTest("admin_edit_assignment",
          "admin", "Assignment", "first", "put", True),
    PTest("admin_delete_normal",
          "admin", "Assignment", "first", "delete", True),
    PTest("staff_delete_normal",
          "staff", "Assignment", "first", "delete", True),
    PTest("admin_grade_normal",
          "admin", "Assignment", "first", "grade", True),
    PTest("staff_grade_normal",
          "staff", "Assignment", "first", "grade", True),
    PTest("staff_staff_normal",
          "staff", "Assignment", "first", "staff", True),
    PTest("admin_delete_empty",
          "admin", "Assignment", "empty", "delete", True),
    PTest("admin_staff_empty",
          "admin", "Assignment", "empty", "staff", True),
    PTest("admin_staff_normal",
          "admin", "Assignment", "first", "staff", True),
    PTest("staff_delete_empty",
          "staff", "Assignment", "empty", "delete", True),
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
