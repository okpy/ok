from models import core
from unittest import mock
import ok
import os
import sys
import unittest

DEMO = 'demo_assignments'
INVALID = os.path.join(DEMO, 'invalid')
VALID = os.path.join(DEMO, 'valid')

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

    VALID_ASSIGN = os.path.join(VALID, 'hw1', 'tests')
    ASSIGN_NO_INFO = os.path.join(INVALID, 'no_info', 'tests')

    def setUp(self):
        self.sample_test = core.Test()
        self.applyPatches()

    #########
    # Tests #
    #########

    def testMissingInfo(self):
        self.assertRaises(ok.OkException, ok.load_tests,
                          self.ASSIGN_NO_INFO)

    def testLoadValidAssignment(self):
        assignment = ok.load_tests(self.VALID_ASSIGN)
        # TODO(albert): After the "required fields" of the test format
        # are determined, this test should check for those fields.
        self.assertIsInstance(assignment, dict)
        self.assertIn('name', assignment)
        self.assertIn('src_files', assignment)
        self.assertIn('tests', assignment)

        tests = assignment['tests']
        self.assertEqual([self.sample_test, self.sample_test], tests)
        self.assertEqual(2, len(core.Test.serialize.mock_calls))

    #############
    # Utilities #
    #############

    def applyPatches(self):
        """Applies unittest patches (temporary mocks)."""
        # Patch Test.serialize to always return self.sample_test
        serialize_patcher = mock.patch('models.core.Test.serialize',
                                       autospec=core.Test.serialize)
        serialize = serialize_patcher.start()
        serialize.return_value = self.sample_test
        self.addCleanup(serialize_patcher.stop)

class DummyArgs:
    """Placeholder for parsed command-line arguments."""


# TODO(albert): rewrite this test after redefining Protocol interface.
# class TestFileContentsProtocol(unittest.TestCase):
#     VALID_ASSIGN = os.path.join(VALID, 'hw1')
#
#     def setUp(self):
#         cmd_line_args = DummyArgs()
#         self.proto = ok.FileContents(cmd_line_args, [self.VALID_ASSIGN])
#
#     def test_on_start(self):
#         contents = self.proto.on_start()
#         self.assertEqual(1, len(contents))
#         self.assertIn('hw1.py', contents)
#         self.assertIn('def square(x):', contents['hw1.py'])
