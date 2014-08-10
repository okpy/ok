#!/usr/bin/python3

import ok

import os
import sys
import unittest


class TestProtocol(ok.Protocol):
    def __init__(self, args, src_files):
        ok.Protocol.__init__(args, src_files)
        self.called_start = 0
        self.called_interact = 0

    def on_start(self):
        self.called_start += 1

    def on_interact(self):
        self.called_interact += 1


class TestOK(unittest.TestCase):
    def test_parse_input(self):
        old_sys_argv = sys.argv[1:]
        sys.argv[1:] = []
        _ = ok.parse_input() # Does not crash and returns a value.
        sys.argv[1:] = old_sys_argv


class TestLoadTests(unittest.TestCase):
    def setUp(self):
        self.hw1_dir = 'demo_assignments'
        self.hw1_tests = os.path.join(self.hw1_dir, 'hw1_tests.py')

    def test_load_test_file(self):
        for path in [self.hw1_dir, self.hw1_tests]:
            filename, _ = ok.load_test_file(path)
            self.assertEqual(self.hw1_tests, filename)

    def test_load_test_file_with_hint(self):
        curdir = os.curdir
        os.chdir(self.hw1_dir)
        filename, _ = ok.load_test_file('1') # Interpreted as a hint
        self.assertEqual('hw1_tests.py', filename)
        os.chdir(curdir)

    def test_find_test_file_no_hint(self):
        filename, _ = ok.find_test_file(self.hw1_dir)
        self.assertEqual(self.hw1_tests, filename)

    def test_find_test_file_not_found(self):
        self.assertRaises(Exception, ok.find_test_file, ['.'])

    def test_find_test_file_with_hints(self):
        good, bad = '1', '2'
        filename, _ = ok.find_test_file(self.hw1_dir, good)
        self.assertEqual(self.hw1_tests, filename)
        self.assertRaises(Exception, ok.find_test_file, [self.hw1_dir, bad])

    def test_get_assignment(self):
        self.assertIsNone(ok.get_assignment(self.hw1_dir))
        assignment = ok.get_assignment(self.hw1_tests)
        self.assertIn('name', assignment)
        self.assertEqual('hw1', assignment['name'])
        self.assertIn('hw1.py', assignment['src_files'])


class DummyArgs:
    """Placeholder for parsed command-line arguments."""


class TestFileContentsProtocol(unittest.TestCase):
    def setUp(self):
        self.hw1 = 'demo_assignments/hw1.py'
        cmd_line_args = DummyArgs()
        self.proto = ok.FileContents(cmd_line_args, [self.hw1])

    def test_on_start(self):
        contents = self.proto.on_start()
        self.assertEqual(1, len(contents))
        self.assertIn('hw1.py', contents)
        self.assertIn('def square(x):', contents['hw1.py'])



