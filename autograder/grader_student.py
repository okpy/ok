"""
Student autograder utilities.

This file provides a common interface for the CS 61A project
student-side autograder. Students do not need to read or understand
the contents of this file.
"""

import argparse
import hmac
import os
import pdb
import pickle
import random
import re
import readline
import sys
import traceback
import urllib.request
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

logger = sys.stdout = OutputLogger()

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

def underline(line, under='='):
    """Prints an underlined version of the given line with the
    specified underline style.

    PARAMETERS:
    line  -- str
    under -- str; a one-character string that specifies the underline
             style
    """
    print(line + '\n' + under * len(line))

PS1 = '>>> '
PS2 = '... '

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

#####################
# Testing Mechanism #
#####################

def get_name(test):
    """Gets the name of a test.

    PARAMETERS:
    test -- dict; test cases for a question. Expected to contain a key
            'name', which either maps to a string or a iterable of
            strings (in which case the first string will be used)

    RETURNS:
    str; the name of the test
    """
    if type(test['name']) == str:
        return test['name']
    return test['name'][0]

def get_test(tests, question):
    """Retrieves a test for the specified question in the given list
    of tests.

    PARAMETERS:
    tests    -- list of dicts; list of tests
    question -- str; name of test

    RETURNS:
    dict; the test corresponding to question. If no such test is found,
    return None
    """
    for test in tests:
        if 'name' not in test:
            continue
        names = test['name']
        if type(names) == str:
            names = (names,)
        if question in names:
            return test
    print('Tests do not exist for "{}"'.format(question))
    print('Try one of the following:')
    print(*(test['name'][0] for test in tests))

class AutograderConsole():
    """Handles test evaluation and output formatting for a single
    test case.

    An instance of this class is designed to be used for exactly
    one test case. While the run method can technically be called
    more than once, the namespace (self.frame) will retain any changes
    caused by the code; as a result, different behavior may occur
    across multiple calls to run.

    Each instance of this class keeps an output log, which can be
    registered with the OutputLogger class. External code can access
    this log to replay output at a later time.

    This class also supports an interact method, which should only be
    called after calling the run method. interact will start an
    InteractiveConsole with the current state of the namespace. Lines
    that were executed by the run method are also saved to the
    readline history.
    """

    def __init__(self, code, outputs, frame, postamble):
        """Constructor

        PARAMETERS:
        code      -- str; code to be executed. Lines will be determined
                     by the split function. Any preambles should be
                     included here
        outputs   -- list; a sequence of outputs. the length of outputs
                     is assumed to be equal to the number of prompts
                     in the code parameter (each prompt is denoted by
                     a "$ ")
        frame     -- dict; namespace in which the code should be
                     executed. A copy of frame is used, so the orignal
                     frame is not mutated
        postamble -- str; teardown code that should be executed after
                     the test case finishes, even if an early abort
                     occurs
        """
        self.frame = frame.copy()
        self.code = code
        self.outputs = iter(outputs)
        self.error = False
        self.postamble = postamble
        self.log = []

    def run(self):
        """Executes lines of code in the namespace provided to the
        constructor.

        The instance's output log is registered with the OutputLogger
        to capture output. This log can be replayed by external code
        at a later time.

        Formatting is designed to mimic a Python interpreter, with
        uses of PS1 and PS2 for each line of code. Lines of code that
        are executed are also stored in the readline history for use
        with interactive mode.

        The postamble is always executed at the end, even if a test
        error causes a premature abort.
        """
        current  = ''
        lines = split(self.code) + ['']
        logger.register_log(self.log)
        readline.clear_history()
        for i, line in enumerate(lines):
            if line:
                readline.add_history(line.replace('$ ', ''))

            if line.startswith(' ') or self.incomplete(current):
                print(PS2 + line)
                current += line + '\n'
                continue

            if current.startswith('$ '):
                output = next(self.outputs)
                if type(output) == tuple:
                    output = output[0]
                self.exec(current.replace('$ ', ''), output)
                if self.error:
                    break
            else:
                self.exec(current)
                if self.error:
                    break
            current = line + '\n'
            if line != '':
                print(PS1 + line.replace('$ ', ''))
        logger.register_log(None)

    def cleanup(self):
        self.exec(self.postamble)

    def exec(self, expr, expected=None):
        """Executes or evaluates a given expression.

        PARAMETERS:
        expr     -- str; expression to be executed or evaluated
        expected -- str; the expected expression, used to compare
                    against the result of evaluating expr. If expected
                    is not None, the function uses eval instead of
                    exec

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

        All code execution occurs in the namespace provided to the
        constructor. Any changes to the namespace (e.g. variable
        definitions) will be preserved.
        """
        try:
            if expected:
                expect = timed(eval, (expected, self.frame.copy()))
                actual = timed(eval, (expr, self.frame))
            else:
                expect = None
                actual = timed(exec, (expr, self.frame))
        except RuntimeError:
            stacktrace = traceback.format_exc()
            print('Traceback (most recent call last):\n  ...')
            print('\n'.join(split(stacktrace)[-9:-1]))
            print('# Error: maximum recursion depth exceeded.')
            self.error = True
        except TimeoutError as e:
            print('# Error: evaluation exceeded {} seconds.'.format(
                  e.timeout))
            self.error = True
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
                print('# Error: expected', repr(expect), "got",
                      e.__class__.__name__)
            self.error = True
        else:
            if expected:
                print(repr(actual))
            if expected and expect != actual:
                print('# Error: expected', repr(expect), 'got',
                      repr(actual))
                self.error = True

    def interact(self):
        """Starts an InteractiveConsole."""
        sys.stdout = sys.__stdout__
        console = InteractiveConsole(locals=self.frame)
        console.interact('# Interactive console.'
                         ' Type exit() to quit')
        sys.stdout = logger

    @staticmethod
    def incomplete(line):
        """Subroutine for checking if the given line can be a complete
        Python line of code.
        """
        return compile_command(line.replace('$ ', '')) is None

def run(test, global_frame, interactive, preamble, verbose):
    """Runs all test suites for this class.

    PARAMETERS:
    test         -- dict; test cases for a single question
    global_frame -- dict; bindings for the global frame
    interactive  -- bool; True if interactive mode is enabled
    preamble     -- str; preamble that is executed for every test
    verbose      -- bool; True if verbose mode is toggled on

    DESCRIPTION:
    Test suites should be correspond to the key 'suites' in test.
    If no such key exists, run as if zero suites are
    defined. Use the first value corresponding to the key 'name' in
    test as the name of the test.

    RETURNS:
    bool; True if all suites passed.
    """
    name = get_name(test)
    underline('Test ' + name)

    if 'note' in test:
        print(split(test['note'], join_str='\n'))
    if 'cache' in test:
        try:
            cache = compile(split(test['cache'], join_str='\n'),
                            '{} cache'.format(name), 'exec')
            timed(exec, (cache, global_frame))
        except Exception as e:
            print('Cache for', name, 'errored:', e)

    if 'preamble' in test and 'all' in test['preamble']:
        preamble += test['preamble']['all']
    postamble = ''
    if 'postamble' in test and 'all' in test['postamble']:
        postamble = test['postamble']['all']

    total_passed = 0
    total_cases = 0
    for counter, suite in enumerate(test['suites']):
        # Preamble and Postamble
        new_preamble = preamble
        if 'preamble' in test:
            new_preamble += test['preamble'].get(counter, '')
        new_postamble = postamble
        if 'postamble' in test:
            new_postamble += test['postamble'].get(counter, '')

        # Run tests
        passed, abort = run_suite(suite, new_preamble, new_postamble,
                               global_frame, verbose, interactive, total_cases)
        total_passed += passed
        total_cases += sum(1 for case in suite if 'concept' not in case[2] and 'unlock' in case[2])
        if abort:
            break

    locked_cases = sum(1 for suite in test['suites']
                         for case in suite if 'unlock' not in case[2])

    if total_passed == total_cases:
        print('All unlocked tests passed!')
    if locked_cases > 0:
        print('-- NOTE: {} still has {} locked cases! --'.format(name,
              locked_cases))
    print()
    return total_passed == total_cases

def run_suite(suite, preamble, postamble, global_frame, verbose, interactive, cases):
    """Runs tests for a single suite.

    PARAMETERS:
    suite        -- list; each element is a test case, represented as a
                    3-tuple
    preamble     -- str; the preamble that should be run before every
                    test
    postamble    -- str; the postamble that should be run after every
                    test case
    global_frame -- dict; global frame
    verbose      -- bool; True if verbose mode is toggled on
    interactive  -- bool; True if interactive mode is toggled on
    cases        -- int; number of cases that preceded the current
                    suite

    DESCRIPTION:
    Each test case in the parameter suite is represented as a
    3-tuple

        (input, outputs, status)

    where:
    input   -- str; a (possibly multiline) string of Python
               source code
    outputs -- iterable or string; if string, outputs is the
               sole expected output. If iterable, each element
               in outputs should correspond to an input slot
               in input (delimited by '$ ').
    status  -- str; contains substrings to denote status

    For each test, a new frame is created and houses all bindings
    made by the test. The preamble will run first (if it exists)
    before the test input. The postamble will be run after the test.

    Expected output and actual output are tested on shallow equality
    (==). If a test fails, a TestError will be raised that
    contains information about the test.

    The OutputLogger should always be set to standard output before
    calling this function, and it will always be set to standard
    output after leaving this function.

    RETURNS:
    bool; True if not all cases unlocked

    RAISES:
    TestError; contains information about the test that failed.
    """
    passed = 0
    case_num = cases
    preamble = split(preamble, join_str='\n')
    postamble = split(postamble, join_str='\n')
    for case, outputs, status in suite:
        if 'unlock' not in status:
            logger.on()
            return passed, True  # students must unlock first
        elif 'concept' in status and verbose:
            underline('Concept question', under='-')
            print('   ', split(case, join_str='\n    '))
            print('\n    A:', split(outputs[0], join_str='\n    '))
            print()
        if 'concept' in status:
            continue

        case_num += 1
        if not verbose:
            logger.off()
        underline('Case {}'.format(case_num), under='-')

        num_prompts = case.count('$ ')
        case = split(case)
        if num_prompts == 0:
            case[-1] = '$ ' + case[-1]
            num_prompts += 1
        assert num_prompts == len(outputs), 'Improper number of prompts'
        code = preamble + '\n' + '\n'.join(case)
        console = AutograderConsole(code, outputs, global_frame,
                                    postamble)
        console.run()
        if console.error and not verbose:
            logger.on()
            underline('Case {} failed'.format(case_num), under='-')
            print(''.join(console.log).strip())
        if console.error and interactive:
            console.interact()
        console.cleanup()
        print()
        if console.error:
            logger.on()
            return passed, True
        passed += 1
    logger.on()
    return passed, False

#######################
# UNLOCKING MECHANISM #
#######################

def unlock(question, tests):
    """Unlocks a question, given locked_tests and unlocked_tests.

    PARAMETERS:
    question -- str; the name of the test
    tests    -- module; contains a list of locked tests

    DESCRIPTION:
    This function incrementally unlocks all cases in a specified
    question. Students must answer in the order that test cases are
    written. Once a test case is unlocked, it will remain unlocked.

    Persistant state is stored by rewriting the contents of
    tests.pkl. Students should NOT manually change these files.
    """
    hash_key = tests['project_info']['hash_key']
    imports = tests['project_info']['imports']

    test = get_test(tests['tests'], question)
    if test is None:
        return
    name = get_name(test)

    if 'suites' not in test:
        print('No tests to unlock for {}.'.format(name))
        return

    prompt = '?'
    underline('Unlocking tests for {}'.format(name))
    print('At each "{}", type in what you would expect the output to '
          'be if you had implemented {}'.format(prompt, name))
    print('Type exit() to quit')
    print()

    global_frame = {}
    for line in imports:
        exec(line, global_frame)

    def hash_fn(x):
        return hmac.new(hash_key.encode('utf-8'),
                        x.encode('utf-8')).digest()

    preamble = split(tests['preamble'])
    cases = 0
    for suite_num, suite in enumerate(test['suites']):
        if not suite:
            continue
        new_preamble = preamble
        if 'preamble' in test and 'all' in test['preamble']:
            new_preamble = new_preamble + split(test['preamble']['all'])
        if 'preamble' in test and suite_num in test['preamble']:
            new_preamble = new_preamble + split(test['preamble'][suite_num])
        for case_num, case in enumerate(suite):
            if 'concept' not in case[2]:
                cases += 1
            if 'unlock' in case[2]:
                continue
            elif 'concept' in case[2]:
                underline('Concept Question', under='-')
                print(split(case[0], join_str='\n'))
                answer = handle_student_input(case[1][0], prompt, hash_fn)
                if answer is None:
                    return
                case[1] = [answer]
                case[2] += 'unlock'
                print("-- Congratulations, you have unlocked this case! --")
                print()
                continue

            underline('Case {}'.format(cases), under='-')
            num_prompts = case[0].count('$ ')
            test_case = split(case[0])
            if num_prompts == 0:
                test_case[-1] = '$ ' + test_case[-1]
                num_prompts += 1
            assert num_prompts == len(case[1]), 'Improper number of prompts'
            lines = new_preamble + test_case
            outputs = iter(case[1])
            answers = []
            for line in lines:
                if len(lines) > 1 and not line.startswith('$'):
                    if line.startswith(' '): # indented
                        print(PS2 + line)
                    else:
                        print(PS1 + line)
                    continue
                line = line.replace('$ ', '')
                print(PS1 + line)
                answer = handle_student_input(next(outputs), prompt, hash_fn)
                if answer is None:
                    return
                answers.append(answer)
            case[1] = answers
            case[2] += 'unlock'
            print("-- Congratulations, you have unlocked this case! --")
            print()
    print("You are done unlocking tests for this question!")

def handle_student_input(output, prompt, hash_fn):
    """Reads student input for unlocking tests.

    PARAMETERS:
    output  -- str or tuple; if str, represents the hashed version of
               the correct output. If tuple, represents a sequence of
               choices (strings) from which the student can choose
    prompt  -- str; the prompt to display when asking for student input
    hash_fn -- function; hash function

    DESCRIPTION:
    Continually prompt the student for an answer to an unlocking
    question until one of the folliwng happens:

        `1. The student supplies the correct answer, in which case
            the supplied answer is returned
         2. The student aborts abnormally (either by typing 'exit()' or
            using Ctrl-C/D. In this case, return None

    Correctness is determined by hashing student input and comparing
    to the parameter "output", which is a hashed version of the correct
    answer. If the hashes are equal, the student answer is assumed to
    be correct.

    RETURNS:
    str  -- the correct solution (that the student supplied)
    None -- indicates an abnormal exit from input prompt
    """
    answer = output
    correct = False
    while not correct:
        if type(output) == tuple:
            print()
            print("Choose the number of the correct choice:")
            for i, choice in enumerate(random.sample(output, len(output))):
                print('    ' + str(i) + ') ' + split(choice, join_str='\n       '))
                if choice == output[0]:
                    answer = hash_fn(str(i))
        sys.stdout = sys.__stdout__
        try:
            student_input = input(prompt + ' ')
        except (KeyboardInterrupt, EOFError):
            try:
                print('\nExiting unlocker...')
            # When you use Ctrl+C in Windows, it throws
            # two exceptions, so you need to catch both of
            # them.... aka Windows is terrible.
            except (KeyboardInterrupt, EOFError):
                pass
            return
        finally:
            sys.stdout = logger
        if student_input in ('exit()', 'quit()'):
            print('\nExiting unlocker...')
            return
        correct = hash_fn(student_input) == answer
        if not correct:
            print("-- Not quite. Try again! --")
    if type(output) == tuple:
        student_input = output[0]
    return student_input

#########################
# AUTO-UPDATE MECHANISM #
#########################

def check_for_updates(tests, filepath):
    """Checks a remote url for changes to the project tests, and
    applies changes depending on user input.

    PARAMETERS:
    tests    -- dict; contents of tests.pkl
    filepath -- str; remote or local filepath to check

    RETURNS:
    bool; True if new changes were made, False if no changes made or
    error occurred.
    """
    version = tests['project_info']['version']
    if filepath is None:
        filepath = tests['project_info']['remote']
    print('You are running version', version, 'of the autograder')
    print('Changelog url:', filepath)

    filepath = os.path.join(filepath, 'CHANGES')
    if os.path.exists(filepath):
        f = None
        try:
            f = open(filepath, 'r')
            changelog = f.read()
        except IOError as e:
            print("Problems reading changelog from", filepath)
            print(e)
            return False
        finally:
            if f is not None:
                f.close()
    else:
        try:
            data = timed(urllib.request.urlopen, (filepath,), timeout=2)
            changelog = data.read().decode('utf-8')
        except (urllib.error.URLError, urllib.error.HTTPError):
            print("Couldn't check remote autograder at", filepath)
            return False
        except TimeoutError:
            print("Checking for updates timed out.")
            return False
        except ValueError:
            print("No remote or local filepath:", filepath)
            return False
    match = re.match('VERSION ([0-9.]+)', changelog)
    if match and match.group(1) != version:
        print('Version', match.group(1), 'is available.')
        prompt = input('Do you want to automatically download changes? [y/n]: ')
        if 'y' in prompt.lower():
            success = parse_changelog(tests, changelog, filepath)
            return success
        else:
            print('Changes not made.')
    return False

def parse_changelog(tests, changelog, filepath):
    """Parses a changelog and updates the tests with the specified
    changes.

    PARAMTERS:
    tests     -- dict; contents tests.pkl
    changelog -- str
    filepath  -- str; filepath of remote files

    RETURNS:
    bool; True if updates successful
    """
    current_version = tests['project_info']['version']
    parts = changelog.partition('VERSION ' + current_version)
    if len(parts) == 3:     # If Version found
        changelog = parts[0]
    changes = re.split('VERSION ([0-9.]+)', changelog)
    changes = list(reversed(changes)) # most recent changes last
    changes.pop() # split will find empty string before first version
    assert len(changes) % 2 == 0
    num_changes = len(changes) // 2
    for i in range(num_changes):
        version = changes[2*i+1]
        change_header, change_contents = '', ''
        for line in changes[2*i].strip('\n').split('\n'):
            if line.startswith('    ') or line == '':
                change_contents += line[4:] + '\n'
                continue
            if change_header != '':
                try:
                    apply_change(change_header, change_contents, tests,
                                 filepath)
                except AssertionError as e:
                    print("Update error:", e)
                    return False
            change_header = line
            change_contents = ''
        # Apply last change
        try:
            terminate = apply_change(change_header, change_contents, tests, filepath)
        except AssertionError as e:
            print("Update error:", e)
            return False
        if terminate:
            break
            tests['project_info']['version'] = version

    logger.on()
    tests['project_info']['version'] = version
    print("Updated to VERSION " + version)
    if version != changes[-1]:
        print("Please re-run the autograder to check for further "
              "updates")
    else:
        print("Applied changelog:\n")
        print(changelog)
    logger.off()
    return True

CHANGE = 'CHANGE'
APPEND = 'APPEND'
REMOVE = 'REMOVE'
GRADER = 'GRADER'

def apply_change(header, contents, tests, filepath):
    """Subroutine that applies the changes described by the header
    and contents.

    PARAMTERS:
    header   -- str; a line describing the type of change
    contents -- str; contents of change, if applicable
    tests    -- dict; contents of tests.pkl
    filepath -- str; filepath to check remote grader

    RAISES:
    AssertionError; if any invalid changes are attempted.

    RETURNS:
    bool; True if GRADER was updated and 'RESTART' is in the header,
    in which case update should exit immediately
    """
    error_msg = 'invalid change "{}"'.format(header)
    if GRADER in header:
        try:
            url = os.path.join(filepath, 'autograder.py')
            data = timed(urllib.request.urlopen, (url,), timeout=2)
            new_autograder = data.read().decode('utf-8')
        except (urllib.error.URLError, urllib.error.HTTPError):
            raise AssertionError("Couldn't retrive remote update for autograder.py")
        except TimeoutError:
            raise AssertionError("Checking for updates timed out.")
        with open('autograder.py', 'w') as f:
            f.write(new_autograder)
        return 'RESTART' in header

    header = header.split('::')
    assert len(header) == 3, error_msg
    change_type = header[0].strip()
    if 'test' in header[1]:
        test_name = header[1].replace('test', '').strip()
        test = get_test(tests['tests'], test_name)
        target = "test"
    else:
        target = "tests['" + header[1].strip() + "']"
    target += header[2].strip()

    assert target is not None, 'Invalid test to update: {}'.format(test_name)

    if change_type == CHANGE:
        update = "{} = {}".format(target, contents)
    elif change_type == APPEND:
        update = "{}.append({})".format(target, contents)
    elif change_type == REMOVE:
        assert contents == '', "Tried " + REMOVE + " with nonempty contents: " + contents
        update = "del {}".format(target)
    else:
        raise AssertionError(error_msg)
    try:
        exec(update)
    except Exception as e:
        raise AssertionError(e.__class__.__name__ + ": " + str(e) + ": " + update)

##########################
# COMMAND-LINE INTERFACE #
##########################

def run_all_tests():
    """Runs a command line interface for the autograder."""
    parser = argparse.ArgumentParser(description='CS61A autograder')
    parser.add_argument('-u', '--unlock', type=str, 
                        help='Unlocks the specified question')
    parser.add_argument('-q', '--question', type=str,
                        help='Run tests for the specified question')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Display tests that passed')
    parser.add_argument('-a', '--all', action='store_true',
                        help='Runs all tests, regardless of failures')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Enables interactive mode upon failure')
    parser.add_argument('-t', '--timeout', type=int,
                        help='Change timeout length')
    parser.add_argument('-r', '--remote', type=str, default=None,
                        help='Check given filepath or url for updates')
    args = parser.parse_args()

    with open('tests.pkl', 'rb') as f:
        all_tests = pickle.load(f)

    if check_for_updates(all_tests, args.remote):
        with open('tests.pkl', 'wb') as f:
            pickle.dump(all_tests, f, pickle.DEFAULT_PROTOCOL)
        return
    print()

    if args.unlock:
        unlock(args.unlock, all_tests)
        with open('tests.pkl', 'wb') as f:
            pickle.dump(all_tests, f, pickle.DEFAULT_PROTOCOL)
        return

    if args.question:
        tests = get_test(all_tests['tests'], args.question)
        if not tests:
            exit(1)
        tests = [tests]
    else:
        tests = all_tests['tests']

    if args.timeout:
        global TIMEOUT
        TIMEOUT = args.timeout

    global_frame = {}
    for line in all_tests['project_info']['imports']:
        exec(line, global_frame)
    exec(split(all_tests.get('cache', ''), join_str='\n'),
         global_frame)

    for test in tests:
        passed = run(test, global_frame, args.interactive,
                     all_tests['preamble'], args.verbose)
        if not args.all and not passed:
            return
    underline('Note:', under='-')
    print('Remember that the tests in this autograder are not',
          'exhaustive, so try your own tests in the interpreter!')

if __name__ == '__main__':
    run_all_tests()
