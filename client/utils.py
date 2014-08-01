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

def split(src, join_str=None):
    """Splits a (possibly multiline) string of Python input into
    a list, adjusting for common indents based on the first line.

    PARAMETERS:
    src      -- str; (possibly) multiline string of Python input
    join_str -- str or None; if None, leave src as a list of strings.
                If not None, concatenate into one string, using "join"
                as the joining string

    DESCRIPTION:
    Indentation adjustment is determined by the first nonempty
    line. The characters of indentation for that line will be
    removed from the front of each subsequent line.

    RETURNS:
    list of strings; lines of Python input
    str; all lines combined into one string if join is not None
    """
    if not src:
        return [] if not join_str else ''
    src = src.lstrip('\n').rstrip()
    match = re.match('\s+', src)
    length = len(match.group(0)) if match else 0
    result = [line[length:] for line in src.split('\n')]
    if join_str is not None:
        result = join_str.join(result)
    return result

def underline(text, line='='):
    """Prints an underlined version of the given line with the
    specified underline style.

    PARAMETERS:
    line  -- str
    under -- str; a one-character string that specifies the underline
             style
    """
    print(text + '\n' + line * len(text))

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

class ReturningThread(Thread):
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

TIMEOUT = 10
def timed(fn, args=(), kargs={}, timeout=0):
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
    submission = ReturningThread(fn, args, kargs)
    submission.start()
    submission.join(timeout)
    if submission.is_alive():
        raise TimeoutError(timeout)
    if submission.error is not None:
        raise submission.error
    return submission.result

