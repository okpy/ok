from models import core
from protocols import file_contents
from protocols import protocol
from unittest import mock
import exceptions
import ok
import os
import shutil
import sys
import unittest

DEMO = 'demo_assignments'
INVALID = os.path.join(DEMO, 'invalid')
VALID = os.path.join(DEMO, 'valid')
TMP = os.path.join(DEMO, 'tmp')

class TestProtocol(protocol.Protocol):
    def __init__(self, args, src_files):
        protocol.Protocol.__init__(args, src_files)
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

    ASSIGN_NO_INFO = os.path.join(INVALID, 'no_info', 'tests')
    ASSIGN_NO_TESTS = 'bogus'

    VALID_ASSIGN = os.path.join(VALID, 'hw1', 'tests')
    VALID_NAME = 'hw1'
    VALID_VERSION = '1.0'
    VALID_SRC_FILES = ['hw1.py']

    def setUp(self):
        self.sample_test = mock.Mock(spec=core.Test)
        self.applyPatches()
        self.case_map = {}

    #########
    # Tests #
    #########

    def testMissingTests(self):
        self.assertRaises(exceptions.OkException, ok.load_tests,
                          self.ASSIGN_NO_TESTS, self.case_map)

    def testMissingInfo(self):
        self.assertRaises(exceptions.OkException, ok.load_tests,
                          self.ASSIGN_NO_INFO, self.case_map)

    def testLoadValidAssignment(self):
        assignment = ok.load_tests(self.VALID_ASSIGN, self.case_map)
        self.assertIsInstance(assignment, core.Assignment)
        self.assertEqual(self.VALID_NAME, assignment['name'])
        self.assertEqual(self.VALID_VERSION, assignment['version'])
        self.assertEqual(self.VALID_SRC_FILES, assignment['src_files'])

        self.assertEqual([self.sample_test, self.sample_test],
                         assignment.tests)
        self.assertEqual(2, len(core.Test.deserialize.mock_calls))

    #############
    # Utilities #
    #############

    def applyPatches(self):
        """Applies unittest patches (temporary mocks)."""
        # Patch Test.deserialize to always return self.sample_test
        deserialize_patcher = mock.patch('models.core.Test.deserialize',
                                       autospec=core.Test.deserialize)
        deserialize = deserialize_patcher.start()
        deserialize.return_value = self.sample_test
        self.addCleanup(deserialize_patcher.stop)

class TestDumpTests(unittest.TestCase):

    ASSIGN_NAME = 'dummy'

    # Note(albert): I'm not a big fan of using the actual filesystem
    # for tests, but it does allow us to catch odd bugs. I'll leave it
    # like this for the time being.
    def setUp(self):
        self.makeTestDirectory()
        self.assignment = self.makeAssignment()
        self.mock_test = mock.Mock(spec=core.Test)
        self.applyPatches()
        self.case_map = {}

    #########
    # Tests #
    #########

    def testNoTests(self):
        ok.dump_tests(TMP, self.assignment)
        self.assertEqual({ok.INFO_FILE}, self.listTestDir())

        # TODO(albert): this part of the test is broken because Python
        # does not re-import modules. Thus, only one version of info.py
        # can be imported.
        # assignment = ok.load_tests(TMP, self.case_map)
        # self.assertEqual(self.assignment.serialize(),
        #                  assignment.serialize())

    def testSingleTest(self):
        test_json = {'names': ['q1'], 'points': 1}
        self.mock_test.serialize.return_value = test_json
        self.mock_test.name = 'q1'
        self.assignment.add_test(self.mock_test)

        ok.dump_tests(TMP, self.assignment)
        self.assertEqual({ok.INFO_FILE, 'q1.py'}, self.listTestDir())

        # TODO(albert): this part of the test is broken because Python
        # does not re-import modules. Thus, only one version of info.py
        # can be imported.
        # assignment = ok.load_tests(TMP, self.case_map)
        # self.assertEqual([self.mock_test], assignment.tests)

    #############
    # Utilities #
    #############

    def makeTestDirectory(self):
        if os.path.exists(TMP):
            shutil.rmtree(TMP)
        os.makedirs(TMP)

    def makeAssignment(self):
        return core.Assignment.deserialize({
            'name': self.ASSIGN_NAME,
            'version': '1.0',
        })

    def makeTestJson(self, names=None):
        return {
            'names': names or ['q1'],
        }

    def listTestDir(self):
        return {f for f in os.listdir(TMP) if f != '__pycache__'}


    def applyPatches(self):
        """Applies unittest patches (temporary mocks)."""
        # Patch Test.deserialize to always return self.sample_test
        deserialize_patcher = mock.patch('models.core.Test.deserialize',
                                       autospec=core.Test.deserialize)
        self.mock_deserialize = deserialize_patcher.start()
        self.mock_deserialize.return_value = self.mock_test
        self.addCleanup(deserialize_patcher.stop)

class TestFileContentsProtocol(unittest.TestCase):
    SRC_FILE = os.path.join(VALID, 'hw1', 'hw1.py')

    def setUp(self):
        cmd_line_args = mock.Mock()
        self.assignment = mock.MagicMock()
        self.assignment.__getitem__.return_value =  [self.SRC_FILE]
        self.logger = mock.Mock()
        self.proto = file_contents.FileContents(cmd_line_args, self.assignment, self.logger)

    def test_on_start(self):
        contents = self.proto.on_start()
        self.assertEqual(1, len(contents))
        self.assertIn('hw1.py', contents)
        self.assertIn('def square(x):', contents['hw1.py'])
