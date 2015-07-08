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
    PTest("student_get_own",
         "student0", "Submission", "first", "get", True),
    PTest("student_get_other",
         "student1", "Submission", "third", "get", False),
    PTest("student_get_group",
         "student1", "Submission", "group", "get", True),
    PTest("student_get_other_group",
         "student2", "Submission", "group", "get", False),
    PTest("student_index_group",
         "student1", "Submission", "group", "index", True),
    PTest("student_index_other_group",
         "student2", "Submission", "group", "index", False),
    PTest("anon_get_first_own",
         "anon", "Submission", "first", "get", False),
    PTest("anon_get_other",
         "anon", "Submission", "second", "get", False),
    PTest("anon_index_0",
         "anon", "Submission", "first", "index", False),
    PTest("anon_index_1",
         "anon", "Submission", "second", "index", False),
    PTest("staff_get_same_course",
         "staff", "Submission", "first", "get", True),
    PTest("staff_get_other_course",
         "staff", "Submission", "third", "get", False),
    PTest("admin_get_student0",
         "admin", "Submission", "first", "get", True),
    PTest("admin_get_student1",
         "admin", "Submission", "third", "get", True),
    PTest("admin_delete_own_student",
         "admin", "Submission", "first", "delete", False),
    PTest("staff_delete_own_student",
         "admin", "Submission", "first", "delete", False),
    PTest("anon_delete_own_student",
         "anon", "Submission", "first", "delete", False),
    PTest("student_delete_submission",
         "student0", "Submission", "first", "delete", False),
    PTest("student_modify_submission",
         "student0", "Submission", "first", "modify", False),
]

#pylint: disable=no-init, missing-docstring
@ddt
class SubmissionPermissionsUnitTest(PermissionsUnitTest):
    @data(*PERMISSIONS_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
    unittest.main()
