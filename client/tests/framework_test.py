#!/usr/bin/python3

import unittest
import ok

class TestProtocol(ok.Protocol):
    name = "test"

    def __init__(self, args, src_files):
        ok.Protocol.__init__(args, src_files)
        self.called_start = 0
        self.called_interact = 0

    def on_start(self, buf):
        self.called_start += 1

    def on_interact(self, buf):
        self.called_interact += 1

class OkTest(unittest.TestCase):

    def setUp(self):
        self.hw1 = './demo_assignments/hw1.py'
        self.hw1_tests = './demo_assignments/hw1_tests.py'

    def test_parse_input(self):
        _ = ok.parse_input() # Does not crash and returns a value.

    def test_is_src_file(self):
        self.assertTrue(ok.is_src_file('hw1.py'))
        self.assertFalse(ok.is_src_file('hw1_tests.py'))
        self.assertFalse(ok.is_src_file('hw1_tests'))
        self.assertFalse(ok.is_src_file('hw1.html'))
        self.assertFalse(ok.is_src_file('ok.py'))

    def test_get_assignment(self):
        self.assertTrue(ok.get_assignment(self.hw1) == 'hw1')
        self.assertFalse(ok.get_assignment(self.hw1_tests))

    def test_group_by_assignment(self):
        paths = [self.hw1, self.hw1_tests]
        groups = ok.group_by_assignment(paths)
        self.assertIn('hw1', groups)
        self.assertEqual(groups['hw1'], paths[0:1])

    def test_find_assignment(self):
        assignment, src_files = ok.find_assignment(None, '.')
        self.assertEqual(assignment, 'hw1')
        self.assertEqual(src_files, [self.hw1])
        self.assertRaises(Exception, ok.find_assignment, [None, 'tests'])
        self.assertRaises(Exception, ok.find_assignment, ['hw2', '.'])
