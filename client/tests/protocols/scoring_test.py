"""Tests the ScoringProtocol."""

from client.models import core
from client.protocols import grading
from client.protocols import scoring
from client.utils import output
from collections import OrderedDict
from unittest import mock
import unittest

class DisplayBreakdownTest(unittest.TestCase):
    def display(self, expect, scores):
        scores_as_dict = OrderedDict(scores)
        self.assertEqual(expect, scoring.display_breakdown(scores_as_dict))

    def testNoScores(self):
        self.display(0, [])

    def testFullPoints(self):
        self.display(5, [
            ('q1', (2, 2)),
            ('q2', (3, 3)),
        ])

    def testPartialPoints(self):
        self.display(2, [
            ('q1', (1, 2)),
            ('q2', (1, 9)),
        ])

    def testZeroPoints(self):
        self.display(0, [
            ('q1', (0, 2)),
            ('q2', (0, 9)),
        ])

class ScoreTest(unittest.TestCase):
    POINTS = 1

    def setUp(self):
        self.logger = mock.Mock()
        self.mock_test = core.Test(names=['dummy'], points=self.POINTS)

    def makeGradedTestCase(self, error=False, should_grade=True):
        case = grading.GradedTestCase(type=grading.GradedTestCase.type)
        case.on_grade = mock.Mock(return_value=error)
        case.should_grade = mock.Mock(return_value=should_grade)
        return case

    def calls_score(self, test, expect_score, expect_passed, expect_total):
        score, passed, total = scoring.score(test, self.logger)
        self.assertEqual(expect_score, score)
        self.assertEqual(expect_passed, passed)
        self.assertEqual(expect_total, total)

    def testNoSuites(self):
        self.calls_score(self.mock_test, 0, 0, 0)

    def testNoPoints(self):
        self.mock_test['points'] = 0
        self.mock_test.add_suite([
            self.makeGradedTestCase(),
        ])
        self.calls_score(self.mock_test, 0, 1, 1)

    def testOneSuite_noGradedTestCase(self):
        self.mock_test.add_suite([
            core.TestCase(type=core.TestCase.type),
        ])
        self.calls_score(self.mock_test, 0, 0, 0)

    def testOneSuite_oneCasePass(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(),
        ])
        self.calls_score(self.mock_test, self.POINTS, 1, 1)

    def testOneSuite_oneCaseFail(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(error=True),
        ])
        self.calls_score(self.mock_test, 0, 0, 1)

    def testOneSuite_multipleCasePass(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
        ])
        self.calls_score(self.mock_test, self.POINTS, 1, 1)

    def testOneSuite_secondCaseFail(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(error=False),
            self.makeGradedTestCase(error=True),
        ])
        self.calls_score(self.mock_test, 0, 0, 1)

    def testOneSuite_shouldNotGrade(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(should_grade=False),
            self.makeGradedTestCase(),
        ])
        self.calls_score(self.mock_test, self.POINTS, 1, 1)

    def testMultipleSuites_pass(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
        ])
        self.mock_test.add_suite([
            self.makeGradedTestCase(),
            self.makeGradedTestCase(),
        ])
        self.calls_score(self.mock_test, self.POINTS, 2, 2)

    def testMultipleSuites_firstSuiteFail(self):
        self.mock_test.add_suite([
            self.makeGradedTestCase(error=True),
        ])
        self.mock_test.add_suite([
            self.makeGradedTestCase(error=False),
        ])
        self.calls_score(self.mock_test, self.POINTS * 1 / 2, 1, 2)

