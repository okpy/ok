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
PERMISSION_TESTS = [
   PTest("student_get_own",
         "student0", "Message", "first", "get", True),
   PTest("student_get_other",
         "student1", "Message", "third", "get", False),
   PTest("student_get_group",
         "student1", "Message", "group", "get", True),
   PTest("student_get_other_group",
         "student2", "Message", "group", "get", False),
   PTest("student_index_group",
         "student1", "Message", "group", "index", True),
   PTest("student_index_other_group",
         "student2", "Message", "group", "index", False),
   PTest("anon_get_first_own",
         "anon", "Message", "first", "get", False),
   PTest("anon_get_other",
         "anon", "Message", "second", "get", False),
   PTest("anon_index_0",
         "anon", "Message", "first", "index", False),
   PTest("anon_index_1",
         "anon", "Message", "second", "index", False),
   PTest("staff_get_same_course",
         "staff", "Message", "first", "get", True),
   PTest("staff_get_other_course",
         "staff", "Message", "third", "get", False),
   PTest("admin_get_student0",
         "admin", "Message", "first", "get", True),
   PTest("admin_get_student1",
         "admin", "Message", "third", "get", True),
   PTest("admin_delete_own_student",
         "admin", "Message", "first", "delete", False),
   PTest("staff_delete_own_student",
         "admin", "Message", "first", "delete", False),
   PTest("anon_delete_own_student",
         "anon", "Message", "first", "delete", False),
   PTest("student_delete_submission",
         "student0", "Message", "first", "delete", False),
   PTest("student_modify_submission",
         "student0", "Message", "first", "modify", False),
]

#pylint: disable=no-init, missing-docstring
@ddt
class MessagePermissionsUnitTest(PermissionsUnitTest):
    @data(*PERMISSION_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
    unittest.main()
