import readline
import sys
import traceback
from code import InteractiveConsole, compile_command
from utils import (
    Counter,
    OkConsole,
    TimeoutError,
    indent,
    maybe_strip_prompt,
    timed,
    underline,
)

#####################
# Testing Mechanism #
#####################

def run(test, frame, console, interactive=False, verbose=False):
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
    underline('Test ' + test.name)
    if test.note:
        print(test.note)
    if test.cache:
        # TODO(albert): cleanup cache evaluation
        try:
            cache = compile(test.cache,
                            '{} cache'.format(name), 'exec')
            timed(exec, (cache, global_frame))
        except Exception as e:
            print('Cache for', name, 'errored:', e)

    cases_tested = Counter()
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

def _run_suite(suite, frame, console, cases_tested, verbose,
        interactive):
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
            console.logger.on()
            return passed, True  # students must unlock first
        cases_tested.increment()

        if case.is_conceptual and verbose:
            underline('Concept question', line='-')
            print(indent('\n'.join(case.lines), '   '))
            print(indent('A: ' + case.outputs[0].answer, '    '))
            print()
        if case.is_conceptual:
            passed += 1
            continue

        if not verbose:
            console.logger.off()
        underline('Case {}'.format(cases_tested), line='-')

        code = case.lines
        error, log = console.run(case, frame)

        if error and not verbose:
            console.logger.on()
            underline('Case {} failed'.format(cases_tested), line='-')
            print(''.join(log).strip())
        if error and interactive:
            console.interact(frame)

        console.exec(case.teardown, frame)
        print()
        if error:
            console.logger.on()
            return passed, True
        passed += 1
    console.logger.on()
    return passed, False

class TestingConsole(OkConsole):
    """Handles test evaluation and output formatting for a single
    TestCase.

    An instance of this class can be (and should be) reused for
    multiple TestCases. Each instance of this class keeps an output
    log that is registered with the OutputLogger class. External code
    can access this log to replay output at a later time.

    This class also supports an interact method, which should only be
    called after calling the run method. interact will start an
    InteractiveConsole with the current state of the namespace. Lines
    that were executed by the run method are also saved to the
    readline history.
    """
    PS1 = '>>> '
    PS2 = '... '

    def __init__(self, logger, equal_fn=None):
        super().__init__(logger)
        if equal_fn:
            self.equal = equal_fn
        else:
            self.equal = lambda x, y: x == y

    ##################
    # Public methods #
    ##################

    def run(self, case, frame=None):
        """Executes lines of code in the provided frame.

        An output log is registered with the OutputLogger to capture
        output. The log is returned once this method terminates. This
        log can be replayed by external code at a later time.

        Formatting is designed to mimic a Python interpreter, with
        uses of PS1 and PS2 for each line of code. Lines of code that
        are executed are also stored in the readline history for use
        with interactive mode.

        This method assumes the TestCase has correctly formatted lines
        such that all prompts have a leading "$ ". In particular, the
        TestCase should have added a "$ " for the "last line is prompt"
        rule.

        The TestCase's teardown code is not executed at the end. It
        is up to the external application to call exec with teardown
        code.

        RETURNS:
        (error, log), where
        error -- bool; True if an error occurred, False otherwise.
        log   -- list; a list of lines of output, as captured by the
                 OutputLogger.
        """
        # TODO(albert): Windows machines don't have a readline module.
        readline.clear_history()
        self._activate_logger()

        outputs = iter(case.outputs)
        frame = frame.copy() if frame else {}

        error = False
        current  = ''
        for line in case.lines + ['']:
            self.__add_line_to_history(line)
            if line.startswith(' ') or self.__incomplete(current):
                print(self.PS2 + line)
                current += line + '\n'
                continue
            elif current.startswith('$ '):
                output = next(outputs).answer
                error = self.exec(maybe_strip_prompt(current),
                        frame, expected=output)
                if error:
                    break
            else:
                error = self.exec(current, frame)
                if error:
                    break
            current = line + '\n'
            if line != '':
                print(self.PS1 + maybe_strip_prompt(line))
        self._deactivate_logger()
        return error, self.log

    def exec(self, expr, frame, expected=None):
        """Executes or evaluates a given expression in the provided
        frame.

        PARAMETERS:
        expr     -- str; expression to be executed or evaluated.
        frame    -- dict; frame in which expr should be evaluated.
        expected -- str; the expected expression, used to compare
                    against the result of evaluating expr. If expected
                    is not None, the function uses eval instead of
                    exec.

        DESCRIPTION:
        If expected is None, expr is processed using the built-in exec
        function. If expected is a string, expr and expected will be
        processed using the built-in eval function, and will be
        tested for equality as defined by the == operator.

        Errors are caught and printed. Special output messages are used
        for RuntimeErrors (maximum recursion depth) and TimeoutErrors.
        In addition, expected can be a subclass of Exception, in which
        case success occurs only when an instance of that exception is
        raised.

        All code execution occurs in the provided frame. Any changes to
        the frame (e.g. variable definitions) will be preserved.

        RETURNS:
        bool; True if an error occurred or the evaluated expression
        does not equal the expected value, False otherwise.
        """
        try:
            if expected:
                expect = timed(eval, (expected, frame.copy()))
                actual = timed(eval, (expr, frame))
            else:
                expect = None
                actual = timed(exec, (expr, frame))
        except RuntimeError:
            stacktrace_length = 9
            stacktrace = traceback.format_exc().split('\n')
            print('Traceback (most recent call last):\n  ...')
            print('\n'.join(stacktrace[-stacktrace_length:-1]))
            print('# Error: maximum recursion depth exceeded.')
            return True
        except TimeoutError as e:
            print('# Error: evaluation exceeded {} seconds.'.format(
                  e.timeout))
            return True
        except Exception as e:
            if type(expect) == type and \
                    issubclass(expect, BaseException) and \
                    isinstance(e, expect):
                print(e.__class__.__name__ + ':', e)
                return
            stacktrace = traceback.format_exc()
            token = '<module>\n'
            index = stacktrace.rfind(token) + len(token)
            print('Traceback (most recent call last):')
            print(stacktrace[index:])
            if expected is not None:
                print('# Error: expected {0} got {1}'.format(
                    repr(expect), e.__class__.__name__))
            return True
        else:
            if expected:
                print(repr(actual))
            if expected and not self.equal(expect, actual):
                print('# Error: expected {0} got {1}'.format(
                    repr(expect), repr(actual)))
                return True
            else:
                return False

    def interact(self, frame=None):
        """Starts an InteractiveConsole, using the variable bindings
        defined in the given frame.

        Calls to this method do not necessarily have to follow a call
        to the run method. This method can be used to interact with
        any frame.
        """
        self._deactivate_logger()
        if not frame:
            frame = {}
        else:
            frame = frame.copy()
        console = InteractiveConsole(frame)
        console.interact('# Interactive console. Type exit() to quit')

    ###################
    # Private methods #
    ###################

    @staticmethod
    def __add_line_to_history(line):
        """Adds the given line to readline history, only if the line
        is non-empty. If the line starts with a prompt symbol, the
        prompt is stripped from the line.
        """
        if line:
            readline.add_history(maybe_strip_prompt(line))

    @staticmethod
    def __incomplete(line):
        """Check if the given line can be a complete line of Python."""
        line = maybe_strip_prompt(line)
        return compile_command(line) is None

