"""Implements the GradingProtocol, which runs all specified tests
associated with an assignment.

The GradedTestCase interface can be implemented by TestCases that are
compatible with the GradingProtocol.
"""

from models import core
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

def run(test, logger, interactive=False, verbose=False):
    """Runs all suites for the specified test.

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
    utils.underline('Test ' + test.name)
    if test.note:
        print(test.note)
    # TODO(albert): cleanup cache evaluation
    # if test.cache:
    #     try:
    #         cache = compile(test.cache,
    #                         '{} cache'.format(name), 'exec')
    #         utils.timed(exec, (cache, global_frame))
    #     except Exception as e:
    #         print('Cache for', name, 'errored:', e)

    cases_tested = utils.Counter()
    total_passed = 0
    for suite in test.suites:
        passed, error = _run_suite(suite, logger, cases_tested,
                                   verbose, interactive)
        total_passed += passed
        if error:
            break

    # TODO(albert): Move stats printing outside of this function
    # total_cases = test.count_cases
    # if total_cases > 0:
    #     print('Passed: {} ({}%)'.format(total_passed,
    #                                     total_passed/total_cases))
    #     print('Locked: {} ({}%)'.format(test.count_locked,
    #                                     test.count_locked/total_cases))
    # print()
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
        if case.is_locked:
            logger.on()
            return passed, True  # students must unlock first
        elif not isinstance(case, GradedTestCase):
            # TODO(albert): should non-GradedTestCases be counted as
            # passing?
            continue
        cases_tested.increment()

        utils.underline('Case {}'.format(cases_tested), line='-')
        error = case.on_grade(logger, verbose, interactive)
        if error:
            return passed, True
        passed += 1
    logger.on()
    return passed, False

