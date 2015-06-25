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
BACKUP_TESTS = [
   PTest("student_get_own",
         "student0", "Backup", "first", "get", True),
   PTest("student_get_other",
         "student1", "Backup", "third", "get", False),
   PTest("student_get_group",
         "student1", "Backup", "group", "get", True),
   PTest("student_get_other_group",
         "student2", "Backup", "group", "get", False),
   PTest("student_index_group",
         "student1", "Backup", "group", "index", True),
   PTest("student_index_other_group",
         "student2", "Backup", "group", "index", False),
   PTest("anon_get_first_own",
         "anon", "Backup", "first", "get", False),
   PTest("anon_get_other",
         "anon", "Backup", "second", "get", False),
   PTest("anon_index_0",
         "anon", "Backup", "first", "index", False),
   PTest("anon_index_1",
         "anon", "Backup", "second", "index", False),
   PTest("staff_get_same_course",
         "staff", "Backup", "first", "get", True),
   PTest("staff_get_other_course",
         "staff", "Backup", "third", "get", False),
   PTest("admin_get_student0",
         "admin", "Backup", "first", "get", True),
   PTest("admin_get_student1",
         "admin", "Backup", "third", "get", True),
   PTest("admin_delete_own_student",
         "admin", "Backup", "first", "delete", False),
   PTest("staff_delete_own_student",
         "admin", "Backup", "first", "delete", False),
   PTest("anon_delete_own_student",
         "anon", "Backup", "first", "delete", False),
   PTest("student_delete_submission",
         "student0", "Backup", "first", "delete", False),
   PTest("student_modify_submission",
         "student0", "Backup", "first", "modify", False),
]

# TODO: Better place for Submission tests.

#pylint: disable=no-init, missing-docstring
@ddt
class BackupPermissionsUnitTest(PermissionsUnitTest):
    @data(*BACKUP_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
    unittest.main()
