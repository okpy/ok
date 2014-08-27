"""TestCase for doctest-style Python tests.

PythonTestCases follow a line-by-line input format that is designed to
mimic a Python interpreter.
"""

from models import core
from protocols import grading
from protocols import unlock
import code
import readline
import traceback
import utils

class PythonTestCase(grading.GradedTestCase, unlock.UnlockTestCase):
    """TestCase for doctest-style Python tests."""

    PROMPT = '$ '
    PS1 = '>>> '
    PS2 = '... '

    def __init__(self, input_str, outputs, frame=None, test=None,
                 teardown='', **status):
        """Constructor.

        PARAMETERS:
        input_str -- str; the input string, which will be dedented and
                     split along newlines.
        outputs   -- list of TestCaseAnswers
        test      -- Test or None; the test to which this test case
                     belongs.
        frame     -- dict; the environment in which the test case will
                     be executed.
        teardown  -- str; the teardown code. This code will be executed
                     regardless of errors.
        status    -- keyword arguments; statuses for the test case.
        """
        super().__init__(input_str, outputs, test=test, **status)
        self._frame = frame or {}
        self.teardown = utils.dedent(teardown)
        self._lines = self._input_str.splitlines()
        self._format_lines()
        # TODO(albert): check that the number of prompts in lines is
        # equal to the number of outputs

    ##################
    # Public Methods #
    ##################

    @property
    def num_prompts(self):
        """Returns the number of prompts for this test case."""
        return [line.startswith(self.PROMPT)
                for line in self._lines].count(True)

    @property
    def lines(self):
        """Returns lines of code for the test case."""
        return self._lines

    @property
    def type(self):
        return 'python'

    @classmethod
    def strip_prompt(cls, text):
        """Removes a prompt from the start of the text, if it exists.
        Otherwise, the text is left unchanged.
        """
        if text.startswith(cls.PROMPT):
            text = text[len(cls.PROMPT):]
        return text

    ######################################
    # Protocol interface implementations #
    ######################################

    def on_grade(self, logger, verbose, interactive):
        """Implements the GradedTestCase interface."""
        if not verbose:
            logger.off()
        log = []
        logger.register_log(log)

        console = _PythonConsole()
        frame = self._frame.copy()
        error = console.run(self, frame)

        if error and not verbose:
            logger.on()
            print(''.join(log).strip())
        if error and interactive:
            interact(frame)

        console.exec(self.teardown, frame)
        print()

        if error:
            logger.on()
        logger.register_log(None)
        return error

    def on_unlock(self, logger, interact_fn):
        """Implements the UnlockTestCase interface."""
        outputs = iter(self._outputs)
        answers = []
        for line in self.lines:
            if line.startswith(' '):  # Line is indented.
                print(self.PS2 + line)
                continue
            print(self.PS1 + self.strip_prompt(line))
            if line.startswith(self.PROMPT):
                hash_key = self.info['hash_key'].encode('utf-8')
                verify_fn = lambda x, y: hmac.new(hash_key, x.encode('utf-8')).digest() == y
                answer = interact_fn(next(outputs), verify_fn)
                answers.append(core.TestCaseAnswer(answer))
        return answers

    ###################
    # Private methods #
    ###################

    def _format_lines(self):
        """Splits the input string and adds an explicit prompt to the
        last line if there are zero prompts.
        """
        if self._lines and self.num_prompts == 0:
            self._lines[-1] = self.PROMPT + self._lines[-1]
        return self._lines

class _PythonConsole(object):
    """Handles test evaluation and output formatting for a single
    PythonTestCase.

    This class also supports an interact method, which should only be
    called after calling the run method. interact will start an
    InteractiveConsole with the current state of the namespace. Lines
    that were executed by the run method are also saved to the
    readline history.
    """
    PROMPT = PythonTestCase.PROMPT
    PS1 = PythonTestCase.PS1
    PS2 = PythonTestCase.PS2

    def __init__(self, equal_fn=None):
        """Constructor.

        PARAMETERS:
        equal_fn -- function; a function that determines if expected
                    output is equal to actual output.
        """
        if equal_fn:
            self.equal = equal_fn
        else:
            self.equal = lambda x, y: x == y

    ##################
    # Public methods #
    ##################

    def run(self, case, frame=None):
        """Executes lines of code in the provided frame.

        Formatting is designed to mimic a Python interpreter, with
        uses of PS1 and PS2 for each line of code. Lines of code that
        are executed are also stored in the readline history for use
        with interactive mode.

        This method assumes the TestCase has correctly formatted lines
        such that all prompts have a leading prompt. Implicit prompts
        are expected to have been converted to explicit prompts
        beforehand.

        The TestCase's teardown code is not executed at the end. It
        is up to the external application to call exec with teardown
        code.

        RETURNS:
        bool; True if an error occurred, False otherwise.
        """
        # TODO(albert): Windows machines don't have a readline module.
        readline.clear_history()

        outputs = iter(case.outputs)
        frame = frame or {}

        error = False
        current = ''
        for line in case.lines + ['']:
            self._add_line_to_history(line)
            if line.startswith(' ') or self._incomplete(current):
                print(self.PS2 + line)
                current += line + '\n'
                continue
            elif current.startswith(self.PROMPT):
                output = next(outputs).answer
                error = self.exec(PythonTestCase.strip_prompt(current),
                                  frame, expected=output)
                if error:
                    break
            else:
                error = self.exec(current, frame)
                if error:
                    break
            current = line + '\n'
            if line != '':
                print(self.PS1 + PythonTestCase.strip_prompt(line))
        return error

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
        for RuntimeErrors (maximum recursion depth) and Timeouts.
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
                expect = utils.timed(eval, (expected, frame.copy()))
                actual = utils.timed(eval, (expr, frame))
            else:
                expect = None
                actual = utils.timed(exec, (expr, frame))
        except RuntimeError:
            stacktrace_length = 9
            stacktrace = traceback.format_exc().split('\n')
            print('Traceback (most recent call last):\n  ...')
            print('\n'.join(stacktrace[-stacktrace_length:-1]))
            print('# Error: maximum recursion depth exceeded.')
            return True
        except utils.Timeout as e:
            print('# Error: evaluation exceeded {} seconds.'.format(e.timeout))
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
            stacktrace = stacktrace[index:].rstrip('\n')
            if '\n' in stacktrace:
                print('Traceback (most recent call last):')
            print(stacktrace)
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

    ###################
    # Private methods #
    ###################

    @staticmethod
    def _add_line_to_history(line):
        """Adds the given line to readline history, only if the line
        is non-empty. If the line starts with a prompt symbol, the
        prompt is stripped from the line.
        """
        if line:
            readline.add_history(PythonTestCase.strip_prompt(line))

    @staticmethod
    def _incomplete(line):
        """Check if the given line can be a complete line of Python."""
        line = PythonTestCase.strip_prompt(line)
        return code.compile_command(line) is None

def interact(frame=None):
    """Starts an InteractiveConsole, using the variable bindings
    defined in the given frame.

    Calls to this method do not necessarily have to follow a call
    to the run method. This method can be used to interact with
    any frame.
    """
    if not frame:
        frame = {}
    else:
        frame = frame.copy()
    console = code.InteractiveConsole(frame)
    console.interact('# Interactive console. Type exit() to quit')

