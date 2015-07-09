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
	      "student0", "FinalSubmission", "first", "get", True),
	PTest("student_get_other",
	      "student1", "FinalSubmission", "third", "get", False),
	PTest("student_get_group",
	      "student1", "FinalSubmission", "group", "get", True),
	PTest("student_get_other_group",
	      "student2", "FinalSubmission", "group", "get", False),
	PTest("student_index_group",
	      "student1", "Submission", "group", "index", True),
	PTest("student_index_other_group",
	      "student2", "FinalSubmission", "group", "index", False),
	PTest("anon_get_first_own",
	      "anon", "FinalSubmission", "first", "get", False),
	PTest("anon_get_other",
	      "anon", "FinalSubmission", "second", "get", False),
	PTest("anon_index_0",
	      "anon", "FinalSubmission", "first", "index", False),
	PTest("anon_index_1",
	      "anon", "FinalSubmission", "second", "index", False),
	PTest("staff_get_same_course",
	      "staff", "FinalSubmission", "first", "get", True),
	PTest("staff_get_other_course",
	      "staff", "FinalSubmission", "third", "get", False),
	PTest("admin_get_student0",
	      "admin", "FinalSubmission", "first", "get", True),
	PTest("admin_get_student1",
	      "admin", "FinalSubmission", "third", "get", True),
	PTest("admin_delete_own_student",
	      "admin", "FinalSubmission", "first", "delete", False),
	PTest("staff_delete_own_student",
	      "admin", "FinalSubmission", "first", "delete", False),
	PTest("anon_delete_own_student",
	      "anon", "FinalSubmission", "first", "delete", False),
	PTest("student_delete_submission",
	      "student0", "FinalSubmission", "first", "delete", False),
	PTest("student_modify_submission",
	      "student0", "FinalSubmission", "first", "modify", False),
	]

#pylint: disable=no-init, missing-docstring
@ddt
class FinalSubmissionPermissionsUnitTest(PermissionsUnitTest):
	@data(*PERMISSIONS_TESTS) #pylint: disable=star-args
	def test_access(self, value):
		return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
	unittest.main()
