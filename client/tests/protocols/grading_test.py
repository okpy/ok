"""Tests the GradingProtocol."""

from models import core
from protocols import grading
from unittest import mock
import unittest
import utils

class GradeTest(unittest.TestCase):
    def setUp(self):
        self.logger = utils.OutputLogger()

    def makeGradedTestCase(self, error=False, lock=False, input_str='',
            outputs=None, **kargs):
        outputs = outputs or []
        case = grading.GradedTestCase(input_str, outputs, lock=lock,
                **kargs)
        case.on_grade = mock.Mock(return_value=error)
        return case

    def makeTestCase(self, input_str='', outputs=None, lock=False,
            **kargs):
        case = core.TestCase(input_str, outputs or [], lock=lock,
                **kargs)
        return case

    def calls_grade(self, test, expect_passed):
        passed = grading.grade(test, self.logger)
        self.assertEqual(expect_passed, passed)

    def testNoSuites(self):
        test = core.Test()
        self.calls_grade(test, 0)

    def testOneSuite_noGradedTestCase(self):
        test = core.Test()
        test.add_suite([
            self.makeTestCase(test=test),
        ])
        self.calls_grade(test, 0)

    def testOneSuite_oneCasePass(self):
        test = core.Test()
        test.add_suite([
            self.makeGradedTestCase(),
        ])
        self.calls_grade(test, 1)

    def testOneSuite_oneCaseFail(self):
        test = core.Test()
        test.add_suite([
            self.makeGradedTestCase(error=True),
        ])
        self.calls_grade(test, 0)

    def testOneSuite_multipleCasePass(self):
        test = core.Test()
        test.add_suite([
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
        ])
        self.calls_grade(test, 3)

    def testOneSuite_secondCaseFail(self):
        test = core.Test()
        test.add_suite([
            self.makeGradedTestCase(error=False),
            self.makeGradedTestCase(error=True),
        ])
        self.calls_grade(test, 1)

    def testOneSuite_abortLockedTest(self):
        test = core.Test()
        test.add_suite([
            self.makeGradedTestCase(lock=True),
            self.makeGradedTestCase(),
        ])
        self.calls_grade(test, 0)

    def testMultipleSuites_pass(self):
        test = core.Test()
        test.add_suite([
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
        ])
        test.add_suite([
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
        ])
        self.calls_grade(test, 4)

    def testMultipleSuites_firstSuiteFail(self):
        test = core.Test()
        test.add_suite([
            self.makeGradedTestCase(error=True),
        ])
        test.add_suite([
            self.makeGradedTestCase(error=False),
        ])
        self.calls_grade(test, 0)

