"""Implements the ScoringProtocol, which runs all specified tests
associated with an assignment.
"""

from client.models import core
from client.protocols import grading
from client.utils import formatting
from collections import OrderedDict

#####################
# Testing Mechanism #
#####################

class ScoringProtocol(grading.GradingProtocol):
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
        self.scores = OrderedDict()
        if self._grade_all():
            # If testing is successful, print out the point breakdown.
            display_breakdown(self.scores)

    @classmethod
    def add_args(cls, parser):
        parser.add_argument('--score', action='store_true',
                            help="Scores the assignment")

    def _handle_test(self, test):
        """Grades a single Test."""
        formatting.underline('Scoring tests for ' + test.name)
        print()
        points, passed, total = score(test, self.logger, self.args.interactive,
            self.args.verbose, self.args.timeout)

        self.scores[test.name] = (points, test['points'])
        return passed, total
        print()

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

