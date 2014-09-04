"""Tests the PythonTestCase model."""

from models import core
from models import serialize
from unittest import mock
import exceptions
import sys
import unittest
import utils

class MockCase(core.TestCase):
    type = 'mock'

    REQUIRED = {
        'type': serialize.STR,
        'foo': serialize.INT,
    }

class SerializationTest(unittest.TestCase):
    ASSIGN_NAME = 'dummy'
    TEST_NAME = 'q1'
    MAGIC_NUMBER = 42

    GOOD_JSON = {
        'type': MockCase.type,
        'foo': MAGIC_NUMBER,
    }

    BAD_JSON = {
        'type': 'bar',  # Incorrect type for MockCase.
        'foo': MAGIC_NUMBER,
    }

    MALFORMED_JSON = {
        'foo': MAGIC_NUMBER     # Missing type.
    }

    def setUp(self):
        self.assignment = mock.Mock(spec=core.Assignment)
        self.case_map = {MockCase.type: MockCase}

    def testNoCases(self):
        test_json = {'name': self.TEST_NAME, 'points': 2}
        test = core.Test.deserialize(test_json, self.assignment,
                                     self.case_map)

        self.assertEqual(self.TEST_NAME, test.name)
        self.assertEqual(0, test.num_cases)
        self.assertEqual(2, test['points'])

        self.assertEqual(test_json, test.serialize())

    def testSingleSuite(self):
        test_json = {
            'name': self.TEST_NAME,
            'points': 1,
            'suites': [
                [self.GOOD_JSON, self.GOOD_JSON],
            ]
        }
        test = core.Test.deserialize(test_json, self.assignment,
                                     self.case_map)

        self.assertEqual(2, test.num_cases)
        self.assertEqual(1, len(test['suites']))
        self.assertEqual(2, len(test['suites'][0]))

        case1, case2 = test['suites'][0]
        self.assertEqual(self.MAGIC_NUMBER, case1['foo'])
        self.assertEqual(self.MAGIC_NUMBER, case2['foo'])

        self.assertEqual(test_json, test.serialize())

    def testMultipleSuites(self):
        test_json = {
            'name': self.TEST_NAME,
            'points': 2,
            'suites': [
                [self.GOOD_JSON],
                [self.GOOD_JSON],
            ]
        }
        test = core.Test.deserialize(test_json, self.assignment,
                                     self.case_map)

        self.assertEqual(2, test.num_cases)
        self.assertEqual(2, len(test['suites']))
        self.assertEqual(1, len(test['suites'][0]))
        self.assertEqual(1, len(test['suites'][1]))

        case1 = test['suites'][0][0]
        self.assertEqual(self.MAGIC_NUMBER, case1['foo'])
        case2 = test['suites'][1][0]
        self.assertEqual(self.MAGIC_NUMBER, case2['foo'])

        self.assertEqual(test_json, test.serialize())

    def testUnknownType(self):
        test_json = {
            'name': self.TEST_NAME,
            'points': 2,
            'suites': [
                [self.GOOD_JSON],
                [self.BAD_JSON],
            ]
        }
        self.assertRaises(exceptions.DeserializeError, core.Test.deserialize,
                          test_json, self.assignment, self.case_map)

    def testMissingType(self):
        test_json = {
            'name': self.TEST_NAME,
            'points': 2,
            'suites': [
                [self.MALFORMED_JSON],
            ]
        }
        self.assertRaises(exceptions.DeserializeError, core.Test.deserialize,
                          test_json, self.assignment, self.case_map)

