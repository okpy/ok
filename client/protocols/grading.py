"""Implements the GradingProtocol, which runs all specified tests
associated with an assignment.

The GradedTestCase interface should be implemented by TestCases that
are compatible with the GradingProtocol.
"""

from models import core
from protocols import protocol
import utils

#####################
# Testing Mechanism #
#####################

class GradedTestCase(core.TestCase):
    """Interface for tests that can be graded by the grading protocol.
    Subclasses must implement the on_grade method.
    """

    def on_grade(self, logger, verbose, interact):
        """Subclasses that are used by the grading protocol must
        implement this method.

        PARAMETERS:
        logger   -- OutputLogger.
        frame    -- dict; the environment in which the case will be
                    evaluated.
        verbose  -- bool; True if verbose mode is on.
        interact -- bool; True if interact mode is on.

        RETURNS:
        bool; True if the graded test case results in an error.
        """
        raise NotImplementedError

    def should_grade(self):
        """Returns True if this GradedTestCase instance should be
        graded, False otherwise.
        """
        raise NotImplementedError

class GradingProtocol(protocol.Protocol):
    """A Protocol that runs tests, formats results, and sends results
    to the server.
    """
    name = 'grading'

    def on_interact(self):
        """Run gradeable tests and print results."""
        utils.print_title('Running tests for {}'.format(self.assignment['name']))

        # TODO(albert): clean up the case where the test is not
        # recognized.
        any_graded = False
        for test in self.assignment.tests:
            if not self.args.question or self.args.question in test['names']:
                self._grade_test(test)
                any_graded = True
        if not any_graded and self.args.question:
            print('Test {} does not exist. Try one of the following:'.format(self.args.question))
            print(' '.join(sorted(test.name for test in self.assignment.tests)))

    def _grade_test(self, test):
        """Grades a single Test."""
        utils.underline('Running tests for ' + test.name)
        print()
        if test['note']:
            print(test['note'])
        total_passed = grade(test, self.logger, self.args.interactive,
                             self.args.verbose)

        total_cases = test.num_cases
        if total_cases > 0:
            print('== {} ({}%) cases passed for {} =='.format(total_passed,
                                            round(100 * total_passed / total_cases, 2),
                                            test.name))
        if test.num_locked > 0:
            print('-- There are still {} locked test cases.'.format(test.num_locked) + \
            ' Use the -u flag to unlock them. --')
        print()

def grade(test, logger, interactive=False, verbose=False):
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
    cases_tested = utils.Counter()
    total_passed = 0
    for suite in test['suites']:
        passed, error = _run_suite(suite, logger, cases_tested,
                                   verbose, interactive)
        total_passed += passed
        if error:
            break
    return total_passed

def _run_suite(suite, logger, cases_tested, verbose, interactive):
    """Runs tests for a single suite.

    PARAMETERS:
    suite        -- list; each element is a TestCase
    logger       -- OutputLogger.
    cases_tested -- Counter; an object that keeps track of the
                    number of cases that have been tested so far.
    verbose      -- bool; True if verbose mode is toggled on
    interactive  -- bool; True if interactive mode is toggled on

    RETURNS:
    (passed, errored), where
    passed  -- int; number of TestCases that passed
    errored -- bool; True if a TestCase resulted in error.
    """
    passed = 0
    for case in suite:
        if not isinstance(case, GradedTestCase):
            # TODO(albert): should non-GradedTestCases be counted as
            # passing?
            continue
        elif not case.should_grade():
            logger.on()
            return passed, True  # students must unlock first
        cases_tested.increment()

        utils.underline('Case {}'.format(cases_tested), line='-')
        error = case.on_grade(logger, verbose, interactive)
        if error:
            return passed, True
        passed += 1
    logger.on()
    return passed, False

