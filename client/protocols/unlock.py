"""Implements the UnlockProtocol, which unlocks all specified tests
associated with an assignment.

The UnlockTestCase interface can be implemented by TestCases that are
compatible with the UnlockProtocol.
"""

from client.models import core
from client.models import serialize
from client.protocols import protocol
from client.utils import formatting
import hmac
import random
import string

try:
    import readline
    HAS_READLINE = True
except ImportError:
    HAS_READLINE = False


def normalize(text):
    """Normalizes whitespace in a specified string of text."""
    return " ".join(text.split())

class UnlockTestCase(core.TestCase):
    """Interface for tests that can be unlocked by the unlock protocol.
    Subclasses must implement the on_unlock method.
    """

    OPTIONAL = {
        'locked': serialize.BOOL_FALSE,
        'never_lock': serialize.BOOL_FALSE,
        'hidden': serialize.BOOL_FALSE,
    }

    def on_unlock(self, logger, interact_fn):
        """Subclasses that are used by the unlocking protocol must
        implement this method.

        PARAMETERS:
        logger      -- OutputLogger.
        interact_fn -- function; a function that handles interactive
                       input from students.
        """
        raise NotImplementedError

    def on_lock(self, hash_fn):
        """Subclasses that are used by the unlocking protocol must
        implement this method.
        """
        raise NotImplementedError

####################
# Locking Protocol #
####################

class LockProtocol(protocol.Protocol):
    """Locking protocol that wraps that mechanism."""

    name = 'lock'

    def on_start(self):
        """Responsible for locking each test."""
        if self.args.lock:
            formatting.print_title('Locking tests for {}'.format(
                self.assignment['name']))

            if self.assignment['hidden_params']:
                self.assignment['hidden_params'] = {}
                print('* Removed hidden params for assignment')

            for test in self.assignment.tests:
                lock(test, self._hash_fn)
            print('Completed locking {}.'.format(self.assignment['name']))
            print()

    @property
    def _alphabet(self):
        return string.ascii_lowercase + string.digits

    def _hash_fn(self, text):
        text = normalize(text)
        return hmac.new(self.assignment['name'].encode('utf-8'),
                        text.encode('utf-8')).hexdigest()

def lock(test, hash_fn):
    formatting.underline('Locking Test ' + test.name, line='-')

    if test['hidden_params']:
        test['hidden_params'] = {}
        print('* Removed hidden params')

    num_cases = 0
    for suite in test['suites']:
        for case in list(suite):
            num_cases += 1  # 1-indexed
            if case['hidden']:
                suite.remove(case)
                print('* Case {}: removed hidden test'.format(num_cases))
            elif not case['never_lock'] and not case['locked']:
                case.on_lock(hash_fn)
                print('* Case {}: locked test'.format(num_cases))
            elif case['never_lock']:
                print('* Case {}: never lock'.format(num_cases))
            elif case['locked']:
                print('* Case {}: already locked'.format(num_cases))

######################
# UNLOCKING PROTOCOL #
######################

class UnlockProtocol(protocol.Protocol):
    """Unlocking protocol that wraps that mechanism."""

    name = 'unlock'

    def on_interact(self):
        """
        Responsible for unlocking each test.
        """
        if not self.args.unlock:
            return
        formatting.print_title('Unlocking tests for {}'.format(
            self.assignment['name']))

        print('At each "{}",'.format(UnlockConsole.PROMPT)
              + ' type in what you would expect the output to be.')
        print('Type {} to quit'.format(UnlockConsole.EXIT_INPUTS[0]))

        for test in self._filter_tests():
            if test.num_cases == 0:
                print('No tests to unlock for {}.'.format(test.name))
            else:
                formatting.underline('Unlocking tests for {}'.format(test.name))
                print()
                # TODO(albert): the unlock function returns the number
                # of unlocked test cases. This can be a useful metric
                # for analytics in the future.
                cases_unlocked, end_session = unlock(
                    test, self.logger, self.assignment['name'], self.analytics)
                if end_session:
                    break
                print()
        return self.analytics

    def _filter_tests(self):
        """
        Filter out tests based on command line options passed in by the
        student.
        """
        if self.args.question:
            return [test for test in self.assignment.tests
                    if self.args.question in test['names']]
        return self.assignment.tests

def unlock(test, logger, hash_key, analytics=None):
    """Unlocks TestCases for a given Test.

    PARAMETERS:
    test   -- Test; the test to unlock.
    logger -- OutputLogger.
    hash_key -- string; hash_key to be used to unlock.
    analytics -- dict; dictionary used to store analytics for this protocol

    DESCRIPTION:
    This function incrementally unlocks all TestCases in a specified
    Test. Students must answer in the order that TestCases are
    written. Once a TestCase is unlocked, it will remain unlocked.

    RETURN:
    int, bool; the number of cases that are newly unlocked for this Test
    after going through an unlocking session and whether the student wanted
    to exit the unlocker or not.
    """
    if analytics is None:
        analytics = {}
    console = UnlockConsole(logger, hash_key, analytics)
    cases = 0
    cases_unlocked = 0
    analytics[test.name] = []
    analytics['current'] = test.name
    for suite in test['suites']:
        for case in suite:
            cases += 1
            if not isinstance(case, UnlockTestCase) \
                    or not case['locked']:
                continue
            formatting.underline('Case {}'.format(cases), line='-')
            if console.run(case):   # Abort unlocking.
                return cases_unlocked, True
            cases_unlocked += 1
    print("You are done unlocking tests for this question!")
    del analytics['current']
    return cases_unlocked, False

class UnlockException(BaseException):
    """Exception raised by the UnlockConsole."""
    pass

class UnlockConsole(object):
    """Handles an interactive session for unlocking a TestCase."""
    PROMPT = '? '       # Prompt that is used for user input.
    EXIT_INPUTS = (     # Valid user inputs for aborting the session.
        'exit()',
        'quit()',
    )

    def __init__(self, logger, hash_key, analytics=None):
        self._logger = logger
        self._hash_key = hash_key
        self._analytics = analytics

    ##################
    # Public methods #
    ##################

    def run(self, case):
        """Runs an interactive session for unlocking a single TestCase.

        PARAMETERS:
        case -- UnlockTestCase

        DESCRIPTION:
        Upon successful completion, the provided TestCase will be
        marked as unlocked. If the user aborts before successful
        completion, the TestCase will left untouched.

        RETURNS:
        bool; True if an error/abort occurs, False if the TestCase is
        unlocked successfully.
        """
        try:
            case.on_unlock(self._logger, self._interact)
        except UnlockException:
            print('\nExiting unlocker...')
            return True
        else:
            case['locked'] = False
            print("-- Congratulations, you unlocked this case! --")
            print()
            return False

    ###################
    # Private Methods #
    ###################

    def _verify(self, guess, locked):
        return hmac.new(self._hash_key.encode('utf-8'),
                        guess.encode('utf-8')).hexdigest() == locked

    def _input(self, prompt):
        """Retrieves user input from stdin."""
        return input(prompt)

    def _display_choices(self, choices):
        """Prints a mapping of numbers to choices and returns the
        mapping as a dictionary.
        """
        print("Choose the number of the correct choice:")
        choice_map = {}
        for i, choice in enumerate(random.sample(choices, len(choices))):
            i = str(i)
            print(i + ') ' + choice)
            choice_map[i] = choice
        return choice_map

    def _interact(self, answer, choices=None):
        """Reads student input for unlocking tests until the student
        answers correctly.

        PARAMETERS:
        answer    -- str; a locked test case answer.
        choices   -- list or None; a list of choices. If None or an
                     empty list, signifies the question is not multiple
                     choice.

        DESCRIPTION:
        Continually prompt the student for an answer to an unlocking
        question until one of the folliwng happens:

            1. The student supplies the correct answer, in which case
               the supplied answer is returned
            2. The student aborts abnormally (either by typing 'exit()'
               or using Ctrl-C/D. In this case, return None

        Correctness is determined by the verify method.

        RETURNS:
        str  -- the correct solution (that the student supplied)
        """
        correct = False
        attempts = 0
        while not correct:
            if choices:
                choice_map = self._display_choices(choices)
            try:
                attempts += 1
                student_input = self._input(self.PROMPT)
            except (KeyboardInterrupt, EOFError):
                try:
                    # TODO(albert): When you use Ctrl+C in Windows, it
                    # throws two exceptions, so you need to catch both
                    # of them. Find a cleaner fix for this.
                    print()
                except (KeyboardInterrupt, EOFError):
                    pass
                self._analytics[self._analytics['current']].append((attempts, correct))
                raise UnlockException
            student_input.strip()
            if student_input in self.EXIT_INPUTS:
                attempts -= 1
                self._analytics[self._analytics['current']].append((attempts, correct))
                raise UnlockException

            self._add_line_to_history(student_input)

            if choices:
                if student_input not in choice_map:
                    student_input = ''
                else:
                    student_input = normalize(choice_map[student_input])
            correct = self._verify(student_input, answer)
            if not correct:
                print("-- Not quite. Try again! --")
                print()
        self._analytics[self._analytics['current']].append((attempts, correct))
        return student_input

    def _add_line_to_history(self, line):
        """Adds the given line to readline history, only if the line
        is non-empty.
        """
        if line and HAS_READLINE:
            readline.add_history(line)
