"""Tests the GradingProtocol."""

from models import core
from protocols import grading
from unittest import mock
from utils import output
import unittest

class GradeTest(unittest.TestCase):
    def setUp(self):
        self.logger = output.OutputLogger()
        self.mock_test = core.Test(names=['dummy'], points=1)

    def makeGradedTestCase(self, error=False, should_grade=True):
        case = grading.GradedTestCase(type=grading.GradedTestCase.type)
        case.on_grade = mock.Mock(return_value=error)
        case.should_grade = mock.Mock(return_value=should_grade)
        return case

    def calls_grade(self, test, expect_passed):
        passed = grading.grade(test, self.logger)
        self.assertEqual(expect_passed, passed)

    def testNoSuites(self):
        self.calls_grade(self.mock_test, 0)

    def testOneSuite_noGradedTestCase(self):
        self.mock_test.add_suite([
            core.TestCase(type=core.TestCase.type),
        ])
        self.calls_grade(self.mock_test, 0)

    def testOneSuite_oneCasePass(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(),
        ])
        self.calls_grade(self.mock_test, 1)

    def testOneSuite_oneCaseFail(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(error=True),
        ])
        self.calls_grade(self.mock_test, 0)

    def testOneSuite_multipleCasePass(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
        ])
        self.calls_grade(self.mock_test, 3)

    def testOneSuite_secondCaseFail(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(error=False),
            self.makeGradedTestCase(error=True),
        ])
        self.calls_grade(self.mock_test, 1)

    def testOneSuite_shouldNotGrade(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(should_grade=False),
            self.makeGradedTestCase(),
        ])
        self.calls_grade(self.mock_test, 0)

    def testMultipleSuites_pass(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
        ])
        self.mock_test.add_suite([
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
        ])
        self.calls_grade(self.mock_test, 4)

    def testMultipleSuites_firstSuiteFail(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(error=True),
        ])
        self.mock_test.add_suite([
            self.makeGradedTestCase(error=False),
        ])
        self.calls_grade(self.mock_test, 0)

