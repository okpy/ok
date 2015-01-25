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
USER_TESTS = [
    PTest("student_get_self",
          "student0", "User", "student0", "get", True),
    PTest("student_get_other",
          "student0", "User", "student1", "get", False),
    PTest("staff_get_user_wrong_course",
          "staff", "User", "student2", "get", False),
    PTest("staff_get_user",
          "staff", "User", "student0", "get", True),
    PTest("admin_get_student1",
          "admin", "User", "student1", "get", True),
    PTest("anon_get_student0",
          "anon", "User", "student0", "get", False),
    PTest("anon_get_student1",
          "anon", "User", "student1", "get", False),
    PTest("admin_create_student1",
          "admin", "User", "student1", "create", True),
]

#pylint: disable=no-init, missing-docstring, too-many-public-methods
@ddt
class UserPermissionsUnitTest(PermissionsUnitTest):
    @data(*USER_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
    unittest.main()
