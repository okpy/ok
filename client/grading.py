import readline
import sys
import traceback
import utils

#####################
# Testing Mechanism #
#####################

def run(test, frame, interactive=False, verbose=False):
    """Runs all suites for the specified test, given the specified
    global frame.

    PARAMETERS:
    test        -- Test.
    frame       -- dict; the namespace for a frame.
    console     -- AutograderConsole; this console is reused for all
                   test cases for this Test.
    interactive -- bool; if True, an interactive session will be
                   started upon test failure.
    verbose     -- bool; if True, print all test output, even if the
                   test case passes.

    RETURNS:
    (passed, cases), where
    passed -- int; number of TestCases passed
    cases  -- int; total number of testable TestCases
    """
    utils.underline('Test ' + test.name)
    if test.note:
        print(test.note)
    if test.cache:
        # TODO(albert): cleanup cache evaluation
        try:
            cache = compile(test.cache,
                            '{} cache'.format(name), 'exec')
            utils.timed(exec, (cache, global_frame))
        except Exception as e:
            print('Cache for', name, 'errored:', e)

    cases_tested = utils.Counter()
    total_passed = 0
    for suite in test.suites:
        passed, error = _run_suite(suite, frame, console, cases_tested,
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

def _run_suite(suite, logger, frame, cases_tested, verbose, interactive):
    """Runs tests for a single suite.

    PARAMETERS:
    suite        -- list; each element is a TestCase
    frame        -- dict; global frame
    console      -- AutograderConsole; the same console is used for
                    for all cases in the suite.
    cases_tested -- Counter; an object that keeps track of the
                    number of cases that have been tested so far.
    verbose      -- bool; True if verbose mode is toggled on
    interactive  -- bool; True if interactive mode is toggled on

    DESCRIPTION:
    For each TestCase, a new frame is created and houses all bindings
    made by the test. The TestCase's teardown code will always be
    executed after the primary code is done.

    The OutputLogger with which the TestingConsole is registered
    should always be set to standard output before calling this
    function, and it will always be set to standard output after
    leaving this function.

    RETURNS:
    (passed, errored), where
    passed  -- int; number of TestCases that passed
    errored -- bool; True if the entire Test should abort, False
               otherwise
    """
    passed = 0
    for case in suite:
        if case.is_locked:
            logger.on()
            return passed, True  # students must unlock first
        cases_tested.increment()

        utils.underline('Case {}'.format(cases_tested), line='-')
        error = case.on_grade(logger, frame, verbose, interactive)
        if error:
            return passed, True
        passed += 1
    logger.on()
    return passed, False

