"""Implements the GradingProtocol, which runs all specified tests
associated with an assignment.

The GradedTestCase interface should be implemented by TestCases that
are compatible with the GradingProtocol.
"""

from collections import OrderedDict
from models import core
from protocols import grading
from protocols import protocol
from utils import formatting

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
            underline('Point breakdown')
            for name, (score, total) in scores.items():
                print(name + ': ' + '{}/{}'.format(score, total))
            print()
            total = sum(score for score, _ in scores.values())
            underline('Total score')
            print(total)

    def _score_test(self, test):
        """Grades a single Test."""
        formatting.underline('Scoring tests for ' + test.name)
        print()
        if test['note']:
            print(test['note'])
        suites_passed = grade(test, self.logger, self.args.interactive,
                             self.args.verbose, self.args.timeout)

        total_suites = len(test['suites'])
        if total_suites > 0:
            print('== {} ({}%) suites passed for {} =='.format(
                total_suites, round(100 * suites_passed / total_suites, 2),
                test.name))

        score = suites_passed * total_suites / test['points']
        return score

def grade(test, logger, interactive=False, verbose=False, timeout=10):
    """Grades all suites for the specified test.

    PARAMETERS:
    test        -- Test.
    logger      -- OutputLogger.
    interactive -- bool; if True, an interactive session will be
                   started upon test failure.
    verbose     -- bool; if True, print all test output, even if the
                   test case passes.

    RETURNS:
    int; number of TestCases that passed.
    """
    cases_tested = grading.Counter()
    passed = 0
    for suite in test['suites']:
        _, error = grading.run_suite(suite, logger, cases_tested,
                                   verbose, interactive, timeout)
        passed += 1
        if error:
            break
    return passed

