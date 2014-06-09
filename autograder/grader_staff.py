"""
Staff autograder utilities.

This file provides a common interface for the CS 61A project staff-side
autograder.
"""

import argparse
import os
import re
import sys
import traceback
from code import InteractiveConsole, InteractiveInterpreter, compile_command

# set path for autograder to test current working directory
sys.path[0:0] = [os.getcwd()]


######################
# PRINTING UTILITIES #
######################

def make_output_fns():
    """Returns functions related to printing output."""
    devnull = open(os.devnull, 'w')
    stdout = sys.stdout
    def toggle_output(on):
        """Toggles output between stdout and /dev/null.

        PARAMTERS:
        on -- bool; if True, switch output to stdout; if False, switch
              output to /dev/null
        """
        sys.stdout = stdout if on else devnull

    def emit(*args, **kargs):
        """A function that always prints to stdout.

        PARAMETERS:
        args  -- positional arguments to print
        kargs -- keyword arguments to print
        """
        previous = sys.stdout
        sys.stdout = stdout
        print(*args, **kargs)
        sys.stdout = previous

    return toggle_output, emit

toggle_output, emit = make_output_fns()

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

def display_prompt(line, prompt='>>> '):
    """Formats and prints a given line as if it had been typed in an
    interactive interpreter.

    PARAMETERS:
    line   -- object; represents a line of Python code. If not a
              string, line will be converted using repr. Otherwise,
              expected to contain no newlines for aesthetic reasons
    prompt -- str; prompt symbol. If a space is desired between the
              symbol and input, prompt must contain the space itself
    """
    if type(line) != str:
        line = repr(line)
    print(prompt + line)

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

TIMEOUT = 20
def timed(fn, args=(), kargs={}, timeout=TIMEOUT):
    """Evaluates expr in the given frame.

    PARAMETERS:
    fn      -- function; Python function to be evaluated
    args    -- tuple; positional arguments for fn
    kargs   -- dict; keyword arguments for fn
    timeout -- int; number of seconds before timer interrupt

    RETURN:
    Result of calling fn(*args, **kargs).

    RAISES:
    TimeoutError -- if thread takes longer than timemout to execute
    Error        -- if calling fn raises an error, raise it
    """
    from threading import Thread
    class ReturningThread(Thread):
        """Creates a daemon Thread with a result variable."""
        def __init__(self):
            Thread.__init__(self)
            self.daemon = True
            self.result = None
            self.error = None
        def run(self):
            try:
                self.result = fn(*args, **kargs)
            except Exception as e:
                e._message = traceback.format_exc(limit=2)
                self.error = e
    submission = ReturningThread()
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

class TestError(Exception):
    """Custom exception for autograder."""
    PREAMBLE = -1

    def __init__(self, case=None, frame=None):
        """Constructor.

        PARAMETERS:
        case  -- int; specifies the index of the case in the suite that
                 caused the error. If case == TestError.PREAMBLe,
                 denotes the preamble of the suite that cased the error
        frame -- dict; the global frame right before the error occurred
        """
        super().__init__()
        self.case = case
        self.frame = frame
        self.super_preamble = None

    def get(self, test, suite):
        """Gets the code that caused the error.

        PARAMTERS:
        test  -- dict; the test in which the error occurred
        suite -- int; the index of the suite in which the error
                 occurred

        RETURNS:
        str; the code that caused the error.
        """
        preamble = self.super_preamble + \
                   test.get('preamble', {}).get('all', '') + '\n' + \
                   test.get('preamble', {}).get(suite, '')
        preamble = split(preamble, join_str='\n')
        if self.case == self.PREAMBLE:
            return preamble, ''

        assert 0 <= suite < len(test['suites']), 'Test {} does not have Suite {}'.format(get_name(test), suite)
        assert 0 <= self.case < len(test['suites'][suite]), 'Suite {} does not have Case {}'.format(suite, self.case)
        code, outputs, *status = test['suites'][suite][self.case]
        code = split(code, join_str='\n')
        return preamble + '\n' + code, outputs


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

def run(test, global_frame, final, interactive, super_preamble):
    """Runs all test suites for this class.

    PARAMETERS:
    test           -- dict; test cases for a single question
    global_frame   -- dict; bindings for the global frame
    final          -- bool; True if final scores should be displayed
    interactive    -- bool; True if interacive mode is on
    super_preamble -- str; preamble that is executed for every test

    DESCRIPTION:
    Test suites should be correspond to the key 'suites' in test.
    If no such key exists, run as if zero suites are defined. Use the
    first value corresponding to the key 'name' in test as the name of
    the test. If final is True, will output information about suite
    pass rate.

    By default, the point value of the test is defined as the number
    of suites in the test. If the test has a key called 'points',
    the point value will be scaled relative to the value of 'points'.

    RETURNS:
    2-tuple: (passed, suites), where
    passed -- number of suites that passed
    suites -- total number of suites
    """
    name = get_name(test)
    timeout_message, cache_fail = None, False
    if final:
        toggle_output(True)
        underline('Test ' + name)
        toggle_output(False)
    if global_frame is None:
        global_frame = {}
    if 'suites' not in test:
        test['suites'] = []
    if 'cache' in test:
        try:
            cache = compile(split(test['cache'], join_str='\n'),
                            '{} cache'.format(name), 'exec')
            timed(exec, (cache, global_frame))
        except TimeoutError as e:
            timeout_message = 'Evaluation exceeded {} seconds!'.format(e.timeout)
            cache_fail = True
        except Exception as e:
            timeout_message = str(e)
            cache_fail = True

    preamble = super_preamble
    if 'preamble' in test and 'all' in test['preamble']:
        preamble += test['preamble']['all']
    postamble = ''
    if 'postamble' in test and 'all' in test['postamble']:
        postamble = test['postamble']['all']

    passed = 0
    for counter, suite in enumerate(test['suites']):
        if cache_fail:
            break
        # Preamble and Postamble
        label = '{} suite {}'.format(name, counter)
        new_preamble = preamble
        if 'preamble' in test:
            new_preamble += test['preamble'].get(counter, '')
        new_preamble = compile(split(new_preamble, join_str='\n'),
                           '{} preamble'.format(label), 'exec')
        new_postamble = postamble
        if 'postamble' in test:
            new_postamble += test['postamble'].get(counter, '')
        new_postamble = compile(split(new_postamble, join_str='\n'),
                            '{} postamble'.format(label), 'exec')
        toggle_output(False)
        try:
            run_suite(new_preamble, suite, new_postamble, global_frame)
        except TestError as e:
            exec(new_postamble, e.frame)
            e.super_preamble = super_preamble
            if final:
                toggle_output(True)
            frame = handle_failure(e, test, counter,
                                   global_frame.copy(), interactive)
            exec(new_postamble, frame)
            toggle_output(False)
            # TODO timeout message
        else:
            passed += 1

    if final:
        toggle_output(True)
        print('Suite pass rate: {0}/{1}'.format(passed,
                                              len(test['suites'])))
        print()
    elif passed != len(test['suites']):
        toggle_output(True)
        underline('Test ' + name)
        if timeout_message is not None:
            print(timeout_message)
        print('Test(s) failed!')
        print()
    scale = 1 if 'points' not in test else test['points']/len(test['suites'])
    return (passed*scale, len(test['suites'])*scale)

def test_call(fn, args=(), kargs={}, case=-1, frame={}, exception=None):
    """Attempts to call fn with args and kargs. If a timeout or error
    occurs in the process, raise a TestError.

    PARAMTERS:
    fn    -- function
    args  -- tuple; positional arguments to fn
    kargs -- dict; keyword arguments to fn
    case  -- int; index of case to which the function call belongs
    frame -- dict; current state of the global frame

    RETURNS:
    result of calling fn

    RAISES:
    TestError; if calling fn causes an Exception or Timeout
    """
    try:
        result = timed(fn, args, kargs)
    except Exception as e:
        if type(exception)==type and issubclass(exception, BaseException) and isinstance(e, exception):
            return exception
        raise TestError(case, frame)
    else:
        return result


def run_suite(preamble, suite, postamble, global_frame):
    """Runs tests for a single suite.

    PARAMETERS:
    preamble     -- str; the preamble that should be run before every
                    test
    suite        -- list; each element is a test case, represented as a
                    2-tuple or 3-tuple
    postamble    -- str; the postamble that should be run after every
                    test case
    global_frame -- dict; global frame

    DESCRIPTION:
    Each test case in the parameter suite is represented as a
    3-tuple

        (input, outputs, status)

    where:
    input       -- str; a (possibly multiline) string of Python
                   source code
    outputs     -- iterable or string; if string, outputs is the
                   sole expected output. If iterable, each element
                   in outputs should correspond to an input slot
                   in input (delimited by '$ ').

    For each test, a new frame is created and houses all bindings
    made by the test. The preamble will run first (if it exists)
    before the test input. The postamble will be run after the test.

    Expected output and actual output are tested on shallow equality
    (==). If a test fails, a TestError will be raised that
    contains information about the test.

    RAISES:
    TestError; contains information about the test that failed.
    """
    for case_num, (case, outputs, *status) in enumerate(suite):
        if status and 'concept' in status:
            continue
        frame = global_frame.copy()
        test_call(exec, (preamble, frame),
                  case=TestError.PREAMBLE, frame=frame)
        if type(outputs) != list:
            outputs = [outputs]
        out_iter = iter(outputs)

        current, prompts = '', 0
        lines = split(case) + ['']
        for i, line in enumerate(lines):
            if line.startswith(' ') or compile_command(current.replace('$ ', '')) is None:
                current += line + '\n'
                continue

            if current.startswith('$ ') or \
                    (i == len(lines) - 1 and prompts == 0):
                output = next(out_iter)
                if type(output) == tuple:
                    output = output[0]
                expect = test_call(eval, (output, frame.copy()),
                                   case=case_num, frame=frame)
                actual = test_call(eval, (current.replace('$ ', ''), frame),
                                   case=case_num, frame=frame,
                                   exception=expect)
                if expect != actual:
                    raise TestError(case_num, frame)
            else:
                test_call(exec, (current, frame), case=case_num,
                          frame=frame)
            current = ''
            if line.startswith('$ '):
                prompts += 1
            current += line + '\n'
        exec(postamble, frame)

def handle_failure(error, test, suite_number, global_frame, interactive):
    """Handles a test failure.

    PARAMETERS:
    error        -- TestError; contains information about the failed
                    test
    test         -- dict; contains information about the test
    suite_number -- int; suite number (for informational purposes)
    global_frame -- dict; global frame
    interactive  -- bool; True if interactive mode is enabled

    DESCRIPTION:
    Expected output and actual output are checked with shallow
    equality (==).

    RETURNS:
    bool; True if error actually occurs, which should always be
    the case -- handle_failure should only be called if a test
    fails.
    """
    code_source, outputs = error.get(test, suite_number)
    underline('Suite {0} failed:'.format(suite_number + 1), under='-')
    try:
        compile(code_source.replace('$ ', ''),
               'Test {} suite {} case {}'.format(get_name(test),
               suite_number + 1, error.case), 'exec')
    except SyntaxError as e:
        print('SyntaxError:', e)
        return global_frame

    console = InteractiveConsole(locals=global_frame)

    if type(outputs) != list:
        outputs = [outputs]
    out_iter = iter(outputs)

    current, prompts = '', 0
    lines = split(code_source) + ['']
    for i, line in enumerate(lines):
        if line.startswith(' ') or compile_command(current.replace('$ ', '')) is None:
            current += line + '\n'
            display_prompt(line.replace('$ ', ''), PS2)
            continue

        if current.startswith('$ ') or \
                (i == len(lines) - 1 and prompts == 0):
            try:
                output = next(out_iter)
                if type(output) == tuple:
                    output = output[0]
                expect = handle_test(eval, (output, global_frame.copy()),
                                     console=console, current=current,
                                     interactive=interactive)
                actual = handle_test(eval, (current.replace('$ ', ''), global_frame),
                                     console=console, current=current,
                                     interactive=interactive,
                                     expect=expect)
            except TestError:
                return global_frame
            display_prompt(actual, '')

            if expect != actual:
                print('# Error: expected', repr(expect), 'got', repr(actual))
                if interactive:
                    interact(console)
                print()
                return global_frame
        else:
            try:
                handle_test(exec, (current, global_frame),
                            console=console, current=current,
                            interactive=interactive)
            except TestError:
                return global_frame
        current = ''

        if line.startswith('$ '):
            prompts += 1
        current += line + '\n'
        display_prompt(line.replace('$ ', ''), PS1)

    print()
    return global_frame

def handle_test(fn, args=(), kargs={}, console=None, current='',
                interactive=False, expect=None):
    """Handles a function call and possibly starts an interactive
    console.

    PARAMTERS:
    fn          -- function
    args        -- tuple; positional arguments to fn
    kargs       -- dict; keyword arguments to fn
    console     -- InteractiveConsole
    line        -- str; line that contained call to fn
    interactive -- bool; if True, interactive console will start upon
                   error

    RETURNS:
    result of calling fn

    RAISES:
    TestError if error occurs.
    """
    assert isinstance(console, InteractiveConsole), 'Missing interactive console'
    try:
        result = timed(fn, args, kargs)
    except RuntimeError:
        print('# Error: maximum recursion depth exceeded.',
              'Expected', repr(expect))
        if interactive:
            interact(console)
        print()
        raise TestError()
    except TimeoutError as e:
        print('# Error: evaluation exceeded {} seconds.'.format(e.timeout),
              'Expected', repr(expect))
        if interactive:
            interact(console)
        print()
        raise TestError()
    except Exception as e:
        if type(expect) == type and issubclass(expect, BaseException) and isinstance(e, expect):
            return expect
        stacktrace = traceback.format_exc()
        token = '<module>\n'
        index = stacktrace.rfind(token) + len(token)
        print('Traceback (most recent call last):')
        print(stacktrace[index:])
        print('# Error: expected', repr(expect), "got", e.__class__.__name__)
        if interactive:
            interact(console)
        print()
        raise TestError()
    else:
        return result

def interact(console):
    """Starts an interactive console.

    PARAMTERS:
    console -- InteractiveConsole
    """
    console.resetbuffer()
    console.interact('# Interactive console\n'
                     '# Type exit() to quit')


##########################
# COMMAND-LINE INTERFACE #
##########################

def run_all_tests():
    """Runs a command line interface for the autograder."""
    parser = argparse.ArgumentParser(description='CS61A autograder')
    parser.add_argument('-f', '--final', action='store_true',
                        help='Calculates final scores.')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Starts interactive prompt on error')
    parser.add_argument('-t', '--timeout', type=int,
                        help='Change timeout length')
    args = parser.parse_args()
    if not args.final:
        import sanity_tests as tests
    else:
        import full_tests as tests
    if args.timeout:
        global TIMEOUT
        TIMEOUT = args.timeout

    global_frame = {}
    for line in tests.project_info['imports']:
        exec(line, global_frame)
    global_frame['emit'] = emit # function to force print to stdout
    if hasattr(tests, 'cache'):
        exec(split(tests.cache, join_str='\n'), global_frame)
    results = []
    preamble = tests.preamble if hasattr(tests, 'preamble') else ''
    for test in tests.tests:
        passed, total = run(test, global_frame, args.final, args.interactive, preamble)
        if 'extra' in test and test['extra']:
            total = 0
        results.append((get_name(test), passed, total))
    toggle_output(True)
    if not args.final:
        if not any(map(lambda a: a[1] < a[2], results)):
            print('All public tests passed. '
                 'The final autograder might have additional tests.')
        else:
            print('Not all public tests passed.')
            exit(1)
        return
    underline('Point breakdown:')
    scoreA, maximumA = 0, 0
    scoreB, maximumB = 0, 0
    partners = False
    for test, passed, total in results:
        print('{0}: {1}/{2}'.format(test, passed, total))
        if 'A' in test or 'B' not in test:
            scoreA += passed
            maximumA += total
        if 'B' in test or 'A' not in test:
            scoreB += passed
            maximumB += total
        if 'A' in test or 'B' in test:
            partners = True
    if partners:
        print('Partner A: {0}/{1}'.format(scoreA, maximumA))
        print(scoreA)
        print('Partner B: {0}/{1}'.format(scoreB, maximumB))
        print(scoreB)
    else:
        print('Total: {0}/{1}'.format(scoreA, maximumA))
        print(scoreA)

if __name__ == '__main__':
    run_all_tests()
