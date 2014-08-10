import readline
import sys
import traceback
from code import InteractiveConsole, compile_command
from utils import underline, timed, TimeoutError, indent, dedent, maybe_strip_prompt, OkConsole

class Test(object):
    """Represents all suites for a single test in an assignment."""
    # TODO(albert): fill in stubs

    def __init__(self):
        self.suites = []    # TODO(albert): filter out empty suites
        self.names = []
        self.points = 0
        # TODO(albert): all string values should be dedented
        self.note = ''
        self.cache = ''
        # TODO(albert): setup and teardown are always initialized, for
        # convenience. The values are lists of lines -- some
        # processing is necessary.
        self.setup = {}
        self.teardown = {}

    @property
    def name(self):
        """Gets the canonical name of this test.

        RETURNS:
        str; the name of the test
        """
        return self.names[0]

class TestCase(object):
    """Represents a single test case."""
    # TODO(albert): fill in stubs.
    # Every test case should save all setup and teardown code upon
    # initialization.
    def __init__(self):
        # TODO(albert): validate that the number of prompts in 
        # lines is equal to the number of outputs
        # TODO(albert): scan lines for $; if no $ found, add one to
        # the last line.
        self.__lines = []     # Does not include setup code
        self.__outputs = []   # TestCaseAnswer objects
        self.status = {}
        self.type = ''
        self.test = None    # The Test this case belongs to.
        self.suite_num = 0  # The suite this TestCase belongs to.
        self.num_prompts = 0 # Number of prompts in self.lines.

    @property
    def is_graded(self):
        return not self.is_locked and not self.is_conceptual

    @property
    def is_locked(self):
        return self.status.get('lock', True)

    @property
    def is_conceptual(self):
        return self.status.get('concept', False)

    @property
    def lines(self):
        """Returns lines of code for the setup and actual test case."""
        # TODO(albert)

    @property
    def teardown(self):
        """Returns the teardown code for this particular TestCase."""
        # TODO(albert)

    @property
    def outputs(self):
        return self.__outputs

    def unlock(self):
        self.status.setdefault('lock', False)

    def set_outputs(self, new_outputs):
        self.__outputs = new_outputs

class TestCaseAnswer(object):
    """Represents an answer for a single TestCase."""
    # TODO(albert): fill in stubs.
    def __init__(self, answer, choices=None):
        self.answer = answer
        self.choices = choices or []

    def __eq__(self, other):
        return isinstance(other, TestCaseAnswer) \
                and other.answer == self.answer \
                and other.choices == self.choices

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

    total_passed = 0
    total_cases = 0
    for suite in test.suites:
        passed, abort = __run_suite(suite, frame, console, total_cases,
                 verbose, interactive)
        # TODO(albert): Have better counting -- total should be the
        # number of cases run, not the number cases in a suite.
        total_passed += passed
        total_cases += [case.is_graded for case in suite].count(True)
        if abort:
            break

    locked_cases = [case.is_locked for suite in test.suites
                                   for case in suite].count(True)

    if total_passed == total_cases:
        print('All unlocked tests passed!')
    if locked_cases > 0:
        print('-- NOTE: {} still has {} locked cases! --'.format(
            test.name, locked_cases))
    print()
    return total_passed, total_cases

def __run_suite(suite, frame, console, num_cases, verbose, interactive):
    """Runs tests for a single suite.

    PARAMETERS:
    suite       -- list; each element is a TestCase
    frame       -- dict; global frame
    console     -- AutograderConsole; the same console is used for
                   for all cases in the suite.
    num_cases   -- int; number of cases that preceded the current
                   suite. This is used for numbering TestCases.
    verbose     -- bool; True if verbose mode is toggled on
    interactive -- bool; True if interactive mode is toggled on

    DESCRIPTION:
    For each TestCase, a new frame is created and houses all bindings
    made by the test. The TestCase's teardown code will always be
    executed after the primary code is done.

    Expected output and actual output are tested on shallow equality
    (==). If a test fails, the function will immediately exit.

    The OutputLogger with which the AutograderConsole is registered
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
        elif case.is_conceptual and verbose:
            underline('Concept question', line='-')
            print(indent('\n'.join(case.lines), '   '))
            print(indent('A: ' + case.outputs[0].answer, '    '))
            print()

        if case.is_conceptual:
            continue

        num_cases += 1
        if not verbose:
            console.logger.off()
        underline('Case {}'.format(num_cases), line='-')

        code = case.lines
        error, log = console.run(case, frame)

        if error and not verbose:
            console.logger.on()
            underline('Case {} failed'.format(num_cases), line='-')
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

    @staticmethod
    def exec(expr, frame, expected=None):
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
            if expected and expect != actual:
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

