"""This module contains code related to controlling and writing to stdout."""

import os
import sys

class OutputLogger(object):
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

class LogInterceptor(object):
    """A serializable interceptor object that relays output to a logger object"""
    def __init__(self):
        self._msgs = []

    def info(self, *args):
        self._msgs.append(('info', args))

    def warning(self, *args):
        self._msgs.append(('warning', args))

    def error(self, *args):
        self._msgs.append(('error', args))

    def dump_to_logger(self, log):
        for msg_type, msg in self._msgs:
            if msg_type == 'info':
                log.info(*msg)
            elif msg_type == 'warning':
                log.warning(*msg)
            elif msg_type == 'error':
                log.error(*msg)
