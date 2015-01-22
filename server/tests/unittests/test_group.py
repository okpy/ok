#!/usr/bin/env python
# encoding: utf-8

"""
Tests for groups
"""

import unittest
from test_permissions import PermissionsUnitTest

from ddt import ddt, data

PTest = PermissionsUnitTest.PTest
COURSE_TESTS = [
    PTest("anon_get_group",
          "anon", "Group", "group1", "get", False),
    PTest("admin_get_group",
          "admin", "Group", "group1", "get", True),
]

#pylint: disable=no-init, missing-docstring
@ddt
class GroupPermissionsUnitTest(PermissionsUnitTest):
    @data(*COURSE_TESTS) #pylint: disable=star-args
    def test_access(self, value):
        return PermissionsUnitTest.access(self, value)

if __name__ == "__main__":
    unittest.main()
