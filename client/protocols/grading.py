"""Implements the GradingProtocol, which runs all specified tests
associated with an assignment.

The GradedTestCase interface should be implemented by TestCases that
are compatible with the GradingProtocol.
"""

from client.models import core
from client.protocols import protocol
from client.utils import formatting

#####################
# Testing Mechanism #
#####################

class GradedTestCase(core.TestCase):
    """Interface for tests that can be graded by the grading protocol.
    Subclasses must implement the on_grade method.
    """

    def on_grade(self, logger, verbose, interact, timeout):
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
        """Run gradeable tests and print results and return analytics.

        For this protocol, analytics consists of a dictionary whose key(s) are
        the questions being tested and the value is the number of test cases
        that they passed.
        """
        if self.args.score:
            return
        formatting.print_title('Running tests for {}'.format(
            self.assignment['name']))
        self._grade_all()
        return self.analytics

    def _grade_all(self):
        """Grades the specified test (from the command line), 
        or all tests for the assignment (if no tests specified).

        RETURNS:
        bool; True if grading was successful, False otherwise.
        """
        # TODO(albert): clean up the case where the test is not
        # recognized.
        any_graded = False
        for test in self.assignment.tests:
            if not self.args.question or self.args.question in test['names']:
                passed, total = self._handle_test(test)
                any_graded = True
                self.analytics[test.name] = passed
                if total > 0:
                    print('-- {} cases passed ({}%) for {} --'.format(
                        passed, round(100 * passed / total, 2), test.name))
                print()
        if not any_graded and self.args.question:
            print('Test {} does not exist. Try one of the following:'.format(
                self.args.question))
            print(' '.join(sorted(test.name for test in self.assignment.tests)))
            return False
        return True

    def _handle_test(self, test):
        """Grades a single Test."""
        formatting.underline('Running tests for ' + test.name)
        print()
        if test['note']:
            print(test['note'])
        total_passed = grade(test, self.logger, self.args.interactive,
                             self.args.verbose, self.args.timeout)

        if test.num_locked > 0:
            print('-- There are still {} locked test cases.'.format(
                test.num_locked) + ' Use the -u flag to unlock them. --')
        return total_passed, test.num_cases

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
    cases_tested = Counter()
    total_passed = 0
    for suite in test['suites']:
        passed, error = run_suite(suite, logger, cases_tested,
                                   verbose, interactive, timeout)
        total_passed += passed
        if error:
            break
    return total_passed

def run_suite(suite, logger, cases_tested, verbose, interactive, timeout, stop_fast=True):
    """Runs tests for a single suite.

    PARAMETERS:
    suite        -- list; each element is a TestCase
    logger       -- OutputLogger.
    cases_tested -- Counter; an object that keeps track of the
                    number of cases that have been tested so far.
    verbose      -- bool; True if verbose mode is toggled on
    interactive  -- bool; True if interactive mode is toggled on
    stop_fast    -- bool; True if grading should stop at the first
                    test case where should_grade returns False. If
                    False, grading will continue.

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
        elif stop_fast and not case.should_grade():
            logger.on()
            return passed, True  # students must unlock first
        cases_tested.increment()

        formatting.underline('Case {}'.format(cases_tested), line='-')
        error = case.on_grade(logger, verbose, interactive, timeout)
        if error:
            return passed, True
        passed += 1
    logger.on()
    return passed, False

class Counter(object):
    """Keeps track of a running count of natural numbers."""
    def __init__(self):
        self._count = 0

    @property
    def number(self):
        return self._count

    def increment(self):
        self._count += 1
        return self._count

    def __repr__(self):
        return str(self._count)
