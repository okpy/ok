"""TestCase for doctest-style Python tests.

PythonTestCases follow a line-by-line input format that is designed to
mimic a Python interpreter.
"""

from client import exceptions
from client.models import serialize
from client.protocols import grading
from client.protocols import unlock
from client.utils import formatting
from client.utils import timer
import code
import re
import traceback

# TODO(albert): After v1 is released, come up with a better solution
# (preferably one that is cross-platform).
try:
    import readline
    HAS_READLINE = True
except ImportError:
    HAS_READLINE = False

class DoctestCase(grading.GradedTestCase, unlock.UnlockTestCase):
    """TestCase for doctest-style Python tests."""

    type = 'doctest'

    # Fields.
    REQUIRED = {
        'type': serialize.STR,
    }
    OPTIONAL = {
        'test': serialize.STR,
        'locked': serialize.BOOL_FALSE,
        'hidden': serialize.BOOL_FALSE,
        'teardown': serialize.STR,
        'never_lock': serialize.BOOL_FALSE,
    }

    PS1 = '>>> '
    PS2 = '... '

    def __init__(self, **fields):
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
        super().__init__(**fields)
        self['teardown'] = formatting.dedent(self['teardown'])
        self._lines = []

    ##################
    # Public Methods #
    ##################

    @property
    def lines(self):
        """Returns lines of code for the test case."""
        return self._lines

    ######################################
    # Protocol interface implementations #
    ######################################

    def on_grade(self, logger, verbose, interactive, timeout):
        """Implements the GradedTestCase interface."""
        # TODO(albert): For now, all output is displayed, even if
        # verbosity is toggled off (effectively, the verbosity flag
        # is a nop). This is just to get v1 ready ASAP -- fix this
        # later.
        verbose = True

        if not verbose:
            logger.off()
        log = []
        logger.register_log(log)

        assignment_params = self.assignment.processed_params[self.type]
        test_params = self.test.processed_params[self.type]

        console = _PythonConsole(timeout)
        frame = assignment_params.update_frame({}, console.exec)
        frame = test_params.update_frame(frame, console.exec)

        if console.exec(assignment_params['setup'], frame) \
                or console.exec(test_params['setup'], frame):
            # If any of the setup code errors.
            return True

        error = console.run(self, frame)

        if error and not verbose:
            logger.on()
            print(''.join(log).strip())
        if error and interactive:
            _interact(frame)

        console.exec(assignment_params['teardown'], frame)
        console.exec(test_params['teardown'], frame)
        console.exec(self['teardown'], frame)
        print()

        if error:
            logger.on()
        logger.register_log(None)
        return error

    def should_grade(self):
        return not self['locked']

    def on_unlock(self, logger, interact_fn):
        """Implements the UnlockTestCase interface."""
        for line in self.lines:
            if isinstance(line, str):
                print(line)
            elif isinstance(line, _Answer):
                if not line.locked:
                    print(line.output)
                    continue
                line.output = interact_fn(line.output, line.choices)
                line.locked = False
        self['locked'] = False

    def on_lock(self, hash_fn):
        """Implements the UnlockTestCase interface."""
        for line in self.lines:
            if isinstance(line, _Answer):
                if not line.locked:
                    line.output = hash_fn(line.output)
                    line.locked = True
        self['locked'] = True

    #################
    # Serialization #
    #################

    @classmethod
    def deserialize(cls, case_json, assignment, test):
        """Deserializes a JSON object into a Test object, given a
        particular set of assignment_info.

        PARAMETERS:
        case_json       -- JSON; the JSON representation of the case.
        assignment_info -- JSON; information about the assignment,
                           may be used by TestCases.

        RETURNS:
        Test
        """
        case = super().deserialize(case_json, assignment, test)
        case._format_lines()
        case.assignment = assignment
        case.test = test
        return case

    def serialize(self):
        """Serializes this Test object into JSON format.

        RETURNS:
        JSON as a plain-old-Python-object.
        """
        case = []
        for line in self._lines:
            if isinstance(line, _Answer):
                case.append(line.dump())
            else:
                case.append(line)
        self['test'] = '\n'.join(case)
        return super().serialize()

    ###################
    # Private methods #
    ###################

    @classmethod
    def process_params(cls, obj):
        params = _DoctestParams.deserialize(
            obj['params'].get(cls.type, {}))
        params.update(_DoctestParams.deserialize(
            obj['hidden_params'].get(cls.type, {})))
        return params

    def _format_lines(self):
        """Splits the test string and adds _Answer objects to denote
        prompts.
        """
        self._lines = []
        for line in formatting.dedent(self['test']).splitlines():
            if not line:
                continue
            elif line.startswith(self.PS1) or line.startswith(self.PS2):
                self._lines.append(line)
            elif line.startswith('#'):
                # Assume the last object in lines is an _Answer.
                self._lines[-1].update(line)
            else:
                # Wrap the doctest answer in an object.
                self._lines.append(_Answer(line))

class _Answer(object):
    status_re = re.compile(r'#\s*(.+):\s*(.*)')
    locked_re = re.compile(r'#\s*locked')

    def __init__(self, output, choices=None, explanation='',
                 locked=False):
        self.output = output
        self.choices = choices or []
        self.explanation = explanation
        self.locked = locked

    def dump(self):
        result = [self.output]
        if self.locked:
            result.append('# locked')
        if self.explanation:
            result.append('# explanation: ' + self.explanation)
        if self.choices:
            for choice in self.choices:
                result.append('# choice: ' + choice)
        return '\n'.join(result)

    def update(self, line):
        if self.locked_re.match(line):
            self.locked = True
            return
        match = self.status_re.match(line)
        if not match:
            return
        elif match.group(1) == 'locked':
            self.locked = True
        elif match.group(1) == 'explanation':
            self.explanation = match.group(2)
        elif match.group(1) == 'choice':
            self.choices.append(match.group(2))

class _DoctestParams(serialize.Serializable):
    OPTIONAL = {
        'setup': serialize.STR,
        'teardown': serialize.STR,
        'cache': serialize.STR,
    }

    def __init__(self, **fields):
        super().__init__(**fields)
        self['setup'] = formatting.dedent(self['setup'])
        self['teardown'] = formatting.dedent(self['teardown'])
        self['cache'] = formatting.dedent(self['cache'])
        self._frame = None

    def update_frame(self, frame, exec_fn):
        if self._frame is None:
            self._frame = frame.copy()
            exec_fn(self['cache'], self._frame)
        frame.update(self._frame)
        return frame

    def update(self, other):
        for field in self.OPTIONAL:
            if other[field]:
                self[field] = other[field]

class _PythonConsole(object):
    """Handles test evaluation and output formatting for a single
    PythonTestCase.
    """

    PS1 = DoctestCase.PS1
    PS2 = DoctestCase.PS2
    def __init__(self, timeout, equal_fn=None):
        """Constructor.

        PARAMETERS:
        equal_fn -- function; a function that determines if expected
                    output is equal to actual output.
        """
        self.timeout = timeout
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
        if HAS_READLINE:
            readline.clear_history()

        frame = frame or {}

        error = False
        current = []
        for line in case.lines + ['']:
            if isinstance(line, str):
                if current and line.startswith(self.PS1):
                    error = self.exec('\n'.join(current), frame)
                    if error:
                        break
                    current = []
                if line:
                    print(line)
                line = self._strip_prompt(line)
                self._add_line_to_history(line)
                current.append(line)
            elif isinstance(line, _Answer):
                assert len(current) > 0, 'Answer without a prompt'
                error = self.exec('\n'.join(current), frame,
                                  expected=line.output)
                if error:
                    break
                current = []
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
                expect = timer.timed(self.timeout, eval, (expected, frame.copy()))
                actual = timer.timed(self.timeout, eval, (expr, frame))
            else:
                expect = None
                actual = timer.timed(self.timeout, exec, (expr, frame))
        except RuntimeError:
            stacktrace_length = 9
            stacktrace = traceback.format_exc().split('\n')
            print('Traceback (most recent call last):\n  ...')
            print('\n'.join(stacktrace[-stacktrace_length:-1]))
            print('# Error: maximum recursion depth exceeded.')
            return True
        except exceptions.Timeout as e:
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

    def _add_line_to_history(self, line):
        """Adds the given line to readline history, only if the line
        is non-empty. If the line starts with a prompt symbol, the
        prompt is stripped from the line.
        """
        if line and HAS_READLINE:
            readline.add_history(line)

    def _strip_prompt(self, line):
        """Removes a PS1 or PS2 prompt from the front of the line. If
        the line does not contain a prompt, return it unchanged.
        """
        if line.startswith(self.PS1):
            return line[len(self.PS1):]
        elif line.startswith(self.PS2):
            return line[len(self.PS2):]
        else:
            return line

def _interact(frame=None):
    """Starts an InteractiveConsole, using the variable bindings
    defined in the given frame.
    """
    if not frame:
        frame = {}
    else:
        frame = frame.copy()
    console = code.InteractiveConsole(frame)
    console.interact('# Interactive console. Type exit() to quit')


