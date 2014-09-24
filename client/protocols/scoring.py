"""Implements the GradingProtocol, which runs all specified tests
associated with an assignment.

The GradedTestCase interface should be implemented by TestCases that
are compatible with the GradingProtocol.
"""

from client.models import core
from client.protocols import grading
from client.protocols import protocol
from client.utils import formatting
from collections import OrderedDict

#####################
# Testing Mechanism #
#####################

class ScoringProtocol(protocol.Protocol):
    """A Protocol that runs tests, formats results, and reports a
    student's score.
    """
    name = 'scoring'

    def on_interact(self):
        """Run gradeable tests and print results."""
        if not self.args.score:
            return
        formatting.print_title('Scoring tests for {}'.format(
            self.assignment['name']))

        # TODO(albert): clean up the case where the test is not
        # recognized.
        any_graded = False
        scores = OrderedDict()
        for test in self.assignment.tests:
            if not self.args.question or self.args.question in test['names']:
                score = self._score_test(test)
                scores[test.name] = (score, test['points'])
                any_graded = True
        if not any_graded and self.args.question:
            print('Test {} does not exist. Try one of the following:'.format(
                self.args.question))
            print(' '.join(sorted(test.name for test in self.assignment.tests)))
        else:
            display_breakdown(scores)

    def _score_test(self, test):
        """Grades a single Test."""
        formatting.underline('Scoring tests for ' + test.name)
        print()
        points, passed, total = score(test, self.logger, self.args.interactive,
            self.args.verbose, self.args.timeout)

        if total > 0:
            print('-- {} suites passed ({}%) for {} --'.format(
                passed, round(100 * passed / total, 2),
                test.name))
            print()
        return points

def display_breakdown(scores):
    """Prints the point breakdown given a dictionary of scores.

    RETURNS:
    int; the total score for the assignment
    """
    formatting.underline('Point breakdown')
    for name, (score, total) in scores.items():
        print(name + ': ' + '{}/{}'.format(score, total))
    print()

    total = sum(score for score, _ in scores.values())
    print('Total score:')
    print(total)

    return total

def score(test, logger, interactive=False, verbose=False, timeout=10):
    """Grades all suites for the specified test.

    PARAMETERS:
    test        -- Test.
    logger      -- OutputLogger.
    interactive -- bool; if True, an interactive session will be
                   started upon test failure.
    verbose     -- bool; if True, print all test output, even if the
                   test case passes.

    RETURNS:
    (score, passed, total); where
    score  -- float; score for the Test.
    passed -- int; number of suites that passed.
    total  -- int; total number of suites
    """
    cases_tested = grading.Counter()
    passed, total = 0, 0
    for suite in test['suites']:
        correct, error = grading.run_suite(suite, logger, cases_tested,
                                           verbose, interactive, timeout,
                                           stop_fast=False)
        if error:
            total += 1
        elif not error and correct > 0:
            # If no error but correct == 0, then the suite has no
            # graded test cases.
            total += 1
            passed += 1
    if total > 0:
        score = passed * test['points'] / total
    else:
        score = 0
    return score, passed, total

