#!/usr/bin/python3

import unittest
import ok
import sys


class TestProtocol(ok.Protocol):
    name = "test"

    def __init__(self, args, src_files):
        ok.Protocol.__init__(args, src_files)
        self.called_start = 0
        self.called_interact = 0

    def on_start(self):
        self.called_start += 1

    def on_interact(self):
        self.called_interact += 1


class OkTest(unittest.TestCase):

    def setUp(self):
        self.hw1 = './demo_assignments/hw1.py'
        self.hw1_tests = './demo_assignments/hw1_tests.py'

    def test_parse_input(self):
        old_sys_argv = sys.argv[1:]
        sys.argv[1:] = []
        _ = ok.parse_input() # Does not crash and returns a value.
        sys.argv[1:] = old_sys_argv

    def test_get_assignment(self):
        self.assertIsNone(ok.get_assignment(self.hw1))
        self.assertIsNot(ok.get_assignment(self.hw1_tests), None)

    # TODO Before Merge: Update test script to run Python 3
    # TODO Before Merge: Create tests for find_test_file, load_test_file, and get_src_paths

