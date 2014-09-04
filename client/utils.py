from threading import Thread
import os
import re
import sys
import textwrap
import traceback

# TODO(albert): split these utilities into different files in a utils/
# directory

######################
# PRINTING UTILITIES #
######################

class OutputLogger:
    """Custom logger for capturing and suppressing standard output."""
    # TODO(albert): logger should fully implement output stream.

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

    def is_on(self):
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

    # TODO(albert): rewrite this to be cleaner.
    def __getattr__(self, attr):
        return getattr(self._current_stream, attr)

def dedent(text):
    return textwrap.dedent(text).lstrip('\n').rstrip()

def indent(text, indentation):
    return '\n'.join([indentation + line for line in text.splitlines()])

def underline(text, line='='):
    """Prints an underlined version of the given line with the
    specified underline style.

    PARAMETERS:
    line  -- str
    under -- str; a one-character string that specifies the underline
             style
    """
    print(text + '\n' + line * len(text))

def print_title(text):
    text = '# ' + text + ' #'
    print('#'* len(text))
    print(text)
    print('#'* len(text))
    print()

class Counter(object):
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

def prettyformat(json, indentation='  '):
    """Formats a Python-object into a string in a JSON like way, but
    uses triple quotes for multiline strings.

    PARAMETERS:
    json        -- Python object that is serializable into json.
    indentation -- str; represents one level of indentation

    RETURNS:
    str; the formatted json-like string.
    """
    if isinstance(json, int) or isinstance(json, float):
        return str(json)
    elif isinstance(json, str):
        if '\n' in json:
            return '"""\n' + dedent(json) + '\n"""'
        return repr(json)
    elif isinstance(json, list):
        lst = [indent(prettyformat(elem, indentation), indentation)
                        for elem in json]
        return '[\n' + ',\n'.join(lst) + '\n]'
    elif isinstance(json, dict):
        pairs = []
        for k, v in sorted(json.items()):
            k = prettyformat(k, indentation)
            v = prettyformat(v, indentation)
            pairs.append(indent(k + ': ' + v, indentation))
        return '{\n' + ',\n'.join(pairs) + '\n}'
    else:
        raise exceptions.DeserializeError('Invalid json type: {}'.format(json))

#####################
# TIMEOUT MECHANISM #
#####################

class Timeout(Exception):
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
    Timeout -- if thread takes longer than timemout to execute
    Error        -- if calling fn raises an error, raise it
    """
    if not timeout:
        timeout = TIMEOUT
    submission = __ReturningThread(fn, args, kargs)
    submission.start()
    submission.join(timeout)
    if submission.is_alive():
        raise Timeout(timeout)
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

