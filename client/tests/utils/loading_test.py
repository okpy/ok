from client import exceptions
from client.models import core
from client.utils import loading
from unittest import mock
import os
import shutil
import unittest

DEMO = 'client/demo_assignments'
INVALID = os.path.join(DEMO, 'invalid')
VALID = os.path.join(DEMO, 'valid')
TMP = os.path.join(DEMO, 'tmp')

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
        self.assertRaises(exceptions.OkException, loading.load_tests,
                          self.ASSIGN_NO_TESTS, self.case_map)

    def testMissingInfo(self):
        self.assertRaises(exceptions.OkException, loading.load_tests,
                          self.ASSIGN_NO_INFO, self.case_map)

    def testLoadValidAssignment(self):
        assignment = loading.load_tests(self.VALID_ASSIGN, self.case_map)
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
        deserialize_patcher = mock.patch('client.models.core.Test.deserialize',
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
        self.case_map = {}
        self.assignment = self.makeAssignment()
        self.mock_test = mock.Mock(spec=core.Test)
        self.applyPatches()

    #########
    # Tests #
    #########

    def testNoTests(self):
        loading.dump_tests(TMP, self.assignment)
        self.assertEqual({loading.INFO_FILE}, self.listTestDir())

        # TODO(albert): this part of the test is broken because Python
        # does not re-import modules. Thus, only one version of info.py
        # can be imported.
        # assignment = loading.load_tests(TMP, self.case_map)
        # self.assertEqual(self.assignment.serialize(),
        #                  assignment.serialize())

    def testSingleTest(self):
        test_json = {'names': ['q1'], 'points': 1}
        self.mock_test.serialize.return_value = test_json
        self.mock_test.name = 'q1'
        self.assignment.add_test(self.mock_test)

        loading.dump_tests(TMP, self.assignment)
        self.assertEqual({loading.INFO_FILE, 'q1.py'}, self.listTestDir())

        # TODO(albert): this part of the test is broken because Python
        # does not re-import modules. Thus, only one version of info.py
        # can be imported.
        # assignment = loading.load_tests(TMP, self.case_map)
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
        }, self.case_map)

    def makeTestJson(self, names=None):
        return {
            'names': names or ['q1'],
        }

    def listTestDir(self):
        return {f for f in os.listdir(TMP) if f != '__pycache__'}


    def applyPatches(self):
        """Applies unittest patches (temporary mocks)."""
        # Patch Test.deserialize to always return self.sample_test
        deserialize_patcher = mock.patch('client.models.core.Test.deserialize',
                                       autospec=core.Test.deserialize)
        self.mock_deserialize = deserialize_patcher.start()
        self.mock_deserialize.return_value = self.mock_test
        self.addCleanup(deserialize_patcher.stop)

