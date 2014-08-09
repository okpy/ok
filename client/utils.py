import os
import re
import readline
import sys
import textwrap
import traceback
from code import InteractiveConsole, compile_command
from threading import Thread

######################
# PRINTING UTILITIES #
######################

class OutputLogger:
    """Custom logger for capturing and suppressing standard output."""

    def __init__(self):
        self._current_stream = self._stdout = sys.stdout
        self._devnull = open(os.devnull, 'w')
        self._log = None

    def on(self):
        """Allows print statements to emit to standard output."""
        self._current_stream = self._stdout

    def off(self):
        """Prevents print statements from emitting to standard out."""
        self._current_stream = self._devnull

    def register_log(self, log):
        """Registers the given log so that all calls to write will
        append to the log.

        PARAMETERS:
        log -- list or None; if list, write will append all output to
               log. If None, output is not logged.
        """
        self._log = log

    def isOn(self):
        return self._current_stream == self._stdout

    @property
    def log(self):
        return self._log

    def write(self, msg):
        """Writes msg to the current output stream (either standard
        out or dev/null). If a log has been registered, append msg
        to the log.

        PARAMTERS:
        msg -- str
        """
        self._current_stream.write(msg)
        if type(self._log) == list:
            self._log.append(msg)

    def flush(self):
        self._current_stream.flush()

def dedent(text):
    return textwrap.dedent(text).lstrip('\n').rstrip()

indent = textwrap.indent

def underline(text, line='='):
    """Prints an underlined version of the given line with the
    specified underline style.

    PARAMETERS:
    line  -- str
    under -- str; a one-character string that specifies the underline
             style
    """
    print(text + '\n' + line * len(text))

def maybe_strip_prompt(text):
    if text.startswith('$ '):
        text = text[2:]
    return text

#####################
# TIMEOUT MECHANISM #
#####################

class TimeoutError(Exception):
    """Exception for timeouts."""
    _message = 'Evaluation timed out!'

    def __init__(self, timeout):
        """Constructor.

        PARAMTERS:
        timeout -- int; number of seconds before timeout error occurred
        """
        super().__init__(self)
        self.timeout = timeout

TIMEOUT = 10

def timed(fn, args=(), kargs={}, timeout=TIMEOUT):
    """Evaluates expr in the given frame.

    PARAMETERS:
    fn      -- function; Python function to be evaluated
    args    -- tuple; positional arguments for fn
    kargs   -- dict; keyword arguments for fn
    timeout -- int; number of seconds before timer interrupt (defaults
               to TIMEOUT

    RETURN:
    Result of calling fn(*args, **kargs).

    RAISES:
    TimeoutError -- if thread takes longer than timemout to execute
    Error        -- if calling fn raises an error, raise it
    """
    if not timeout:
        timeout = TIMEOUT
    submission = __ReturningThread(fn, args, kargs)
    submission.start()
    submission.join(timeout)
    if submission.is_alive():
        raise TimeoutError(timeout)
    if submission.error is not None:
        raise submission.error
    return submission.result

class __ReturningThread(Thread):
    """Creates a daemon Thread with a result variable."""
    def __init__(self, fn, args, kargs):
        Thread.__init__(self)
        self.daemon = True
        self.result = None
        self.error = None
        self.fn = fn
        self.args = args
        self.kargs = kargs

    def run(self):
        try:
            self.result = self.fn(*self.args, **self.kargs)
        except Exception as e:
            e._message = traceback.format_exc(limit=2)
            self.error = e

###########
# Console #
###########

class OkConsole:
    """An abstract class that handles console sessions for ok.py.

    An instance of this class can be (and should be) reused for
    multiple TestCases. Each instance of this class keeps an output
    log that is registered with an OutputLogger object. External code
    can access this log to replay output at a later time.
    """
    def __init__(self, logger):
        """Constructor.

        PARAMETERS:
        logger -- OutputLogger
        """
        self.logger = logger
        self.log = None

    ##################
    # Public methods #
    ##################

    def run(self, case):
        """Runs a session of the Console for the given TestCase.

        PARAMETERS:
        case -- TestCase.

        DESCRIPTION:
        Subclasses that override this method should call the
        _read_lines generator method, which handles output logging.
        """
        raise NotImplementedError

    def interact(self, frame=None, msg=''):
        """Starts an InteractiveConsole, using the variable bindings
        defined in the given frame.

        Calls to this method do not necessarily have to follow a call
        to the run method. This method can be used to interact with
        any frame.
        """
        # TODO(albert): logger should fully implement output stream
        # interface so we can avoid doing this swap here.
        sys.stdout = sys.__stdout__
        if not frame:
            frame = {}
        else:
            frame = frame.copy()
        console = InteractiveConsole(frame)
        console.interact(msg)
        sys.stdout = self.logger

    #########################
    # Subclass-able methods #
    #########################

    def _read_lines(self, lines):
        """A generator method that handles output logging and yields
        a list of lines.

        Subclasses should use this method to iterate over lines in the
        run method.
        """
        self.log = []
        self.logger.register_log(self.log)
        # TODO(albert): Windows machines don't have a readline module.
        readline.clear_history()
        for line in lines:
            self._add_line_to_history(line)
            yield line
        self.logger.register_log(None)

    def _add_line_to_history(self, line):
        """Adds the given line to readline history.

        Subclasses can override this method to format the line before
        adding to readline history.
        """
        readline.add_history(line)
