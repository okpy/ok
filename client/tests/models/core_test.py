"""Tests the PythonTestCase model."""

from models import core
from unittest import mock
import sys
import unittest
import utils

class DeserializationTest(unittest.TestCase):
    ASSIGN_NAME = 'dummy'
    TEST_NAME = 'q1'
    MOCK_TYPE = 'mock'
    MOCK_CASE_JSON = {'type': MOCK_TYPE}

    def setUp(self):
        self.assignment = {'name': self.ASSIGN_NAME}
        self.mock_case_instance = mock.Mock()
        self.mock_case = mock.create_autospec(core.TestCase)

        self.mock_case.deserialize = mock.Mock(
                return_value=self.mock_case_instance)
        self.mock_case_instance.serialize = mock.Mock(
                return_value=self.MOCK_CASE_JSON)

        self.case_map = {self.MOCK_TYPE: self.mock_case}

    def testNoCases(self):
        test_json = {'names': [self.TEST_NAME], 'points': 2}
        test = core.Test.deserialize(test_json, self.assignment,
                                     self.case_map)

        self.assertEqual(self.TEST_NAME, test.name)
        self.assertEqual(0, test.num_cases)
        self.assertEqual(2, test['points'])

        self.assertEqual(test_json, test.serialize())

    def testMultipleNames(self):
        test_names = ['a', 'b', 'c']
        test_json = {'names': test_names, 'points': 1}
        test = core.Test.deserialize(test_json, self.assignment,
                                     self.case_map)

        self.assertEqual(test_names, test['names'])

        self.assertEqual(test_json, test.serialize())

    def testSingleSuite(self):
        test_json = {
            'names': [self.TEST_NAME],
            'points': 1,
            'suites': [
                [self.MOCK_CASE_JSON, self.MOCK_CASE_JSON],
            ]
        }
        test = core.Test.deserialize(test_json, self.assignment,
                                     self.case_map)

        self.assertEqual(2, len(self.mock_case.deserialize.mock_calls))
        self.assertEqual([[self.mock_case_instance] * 2], test['suites'])
        self.assertEqual(1, test['points'])

        self.assertEqual(test_json, test.serialize())

    def testMultipleSuites(self):
        test_json = {
            'names': [self.TEST_NAME],
            'points': 2,
            'suites': [
                [self.MOCK_CASE_JSON, self.MOCK_CASE_JSON],
                [self.MOCK_CASE_JSON, self.MOCK_CASE_JSON],
            ]
        }
        test = core.Test.deserialize(test_json, self.assignment,
                                     self.case_map)

        self.assertEqual(4, len(self.mock_case.deserialize.mock_calls))
        self.assertEqual([[self.mock_case_instance] * 2] * 2, test['suites'])
        self.assertEqual(2, test['points'])

        self.assertEqual(test_json, test.serialize())
