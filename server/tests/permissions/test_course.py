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
COURSE_TESTS = [
    PTest("anon_get_course",
          "anon", "Course", "first", "get", True),
    PTest("student_get_course",
          "student0", "Course", "first", "get", True),
    PTest("admin_get_course",
          "admin", "Course", "first", "get", True),
    PTest("student_create_course",
          "student0", "Course", "first", "create", False),
    PTest("student_delete_course",
          "student0", "Course", "first", "delete", False),
    PTest("staff_create_course",
          "staff", "Course", "first", "create", False),
    PTest("staff_delete_course",
          "staff", "Course", "first", "delete", False),
    PTest("admin_create_course",
          "admin", "Course", "first", "create", True),
    PTest("admin_delete_course",
          "admin", "Course", "first", "delete", False),
    PTest("anon_delete_course",
          "anon", "Course", "first", "delete", False),
    PTest("student_modify_course",
          "student0", "Course", "first", "modify", False),
    PTest("staff_modify_course",
          "staff", "Course", "first", "modify", True),
]

#pylint: disable=no-init, missing-docstring
@ddt
class CoursePermissionsUnitTest(PermissionsUnitTest):
    @data(*COURSE_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
    unittest.main()
