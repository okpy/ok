"""Implements the UnlockProtocol, which unlocks all specified tests
associated with an assignment.

The UnlockTestCase interface can be implemented by TestCases that are
compatible with the UnlockProtocol.
"""

from models import core
from utils import serialize
from utils import utils
import ok
import random
import readline


# TODO(albert): move this to locking mechanism
# def __make_hash_fn(hash_key, encoding='utf-8'):
#     def hash_fn(x):
#         return hmac.new(hash_key.encode(encoding),
#                         x.encode(encoding)).digest()
#     return hash_fn
#
# hash_key = tests['project_info']['hash_key']
# __make_hash_fn(hash_key)

class UnlockTestCase(core.TestCase):
    """Interface for tests that can be unlocked by the unlock protocol.
    Subclasses must implement the on_unlock method.
    """

    OPTIONAL = {
        'locked': serialize.BOOL_TRUE,
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

######################
# UNLOCKING PROTOCOL #
######################

class UnlockProtocol(ok.Protocol):
    """Unlocking protocol that wraps that mechanism."""

    name = 'unlock'

    def on_interact(self):
        """
        Responsible for unlocking each test.
        """
        print('At each "{}",'.format(UnlockConsole.PROMPT)
              + ' type in what you would expect the output to be.')
        print('Type {} to quit'.format(UnlockConsole.EXIT_INPUTS[0]))

        for test in self._filter_tests():
            if test.num_cases == 0:
                print('No tests to unlock for {}.'.format(test.name))
            else:
                utils.underline('Unlocking tests for {}'.format(test.name))
                print()
                # TODO(albert): the unlock function returns the number
                # of unlocked test cases. This can be a useful metric
                # for analytics in the future.
                unlock(test, self.logger)

    def _filter_tests(self):
        """
        Filter out tests based on command line options passed in by the
        student.
        """
        if self.args.question:
            return [test for test in self.assignment['tests']
                    if test.name == self.args.question]
        return self.assignment['tests']

def unlock(test, logger):
    """Unlocks TestCases for a given Test.

    PARAMETERS:
    test   -- Test; the test to unlock.
    logger -- OutputLogger.

    DESCRIPTION:
    This function incrementally unlocks all TestCases in a specified
    Test. Students must answer in the order that TestCases are
    written. Once a TestCase is unlocked, it will remain unlocked.

    RETURN:
    int; the number of cases that are newly unlocked for this Test
    after going through an unlocking session.
    """
    console = UnlockConsole(logger)
    cases = 0
    cases_unlocked = 0
    for suite in test['suites']:
        for case in suite:
            cases += 1
            if not isinstance(case, UnlockTestCase) \
                    or not case['locked']:
                continue
            utils.underline('Case {}'.format(cases), line='-')
            if console.run(case):   # Abort unlocking.
                return cases_unlocked
            cases_unlocked += 1
    print("You are done unlocking tests for this question!")
    return cases_unlocked

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

    def __init__(self, logger):
        self._logger = logger

    ##################
    # Public methods #
    ##################

    def run(self, case):
        """Runs an interactive session for unlocking a single TestCase.

        PARAMETERS:
        case -- UnlockTestCase

        DESCRIPTION:
        Upon successful completion, the provided TestCase will be
        modified to contain the unlocked TestCaseAnswer, and the
        TestCase will be marked as unlocked. If the user aborts before
        successful completion, the TestCase will left untouched.

        RETURNS:
        bool; True if an error/abort occurs, False if the TestCase is
        unlocked successfully.
        """
        try:
            case.on_unlock(self._logger, self.interact)
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

    # TODO(albert): verify_fn can be moved to Protocols, not
    # TestCases.
    def interact(self, output, verify_fn):
        """Reads student input for unlocking tests until the student
        answers correctly.

        PARAMETERS:
        output    -- TestCaseAnswer; a locked test case answer.
        verify_fn -- function; a function that verifies that a student
                     answer is equal to an encoded version of the
                     correct answer.

        DESCRIPTION:
        Continually prompt the student for an answer to an unlocking
        question until one of the folliwng happens:

            1. The student supplies the correct answer, in which case
               the supplied answer is returned
            2. The student aborts abnormally (either by typing 'exit()'
               or using Ctrl-C/D. In this case, return None

        Correctness is determined by the verification function passed
        into the constructor. The verification function returns True
        if the student answer matches the locked answer. The student's
        answer is then used as the new TestCaseAnswer of the TestCase.

        RETURNS:
        str  -- the correct solution (that the student supplied)
        """
        correct = False
        while not correct:
            if output.choices:
                choice_map = self._display_choices(output.choices)

            try:
                student_input = self._input(self.PROMPT)
            except (KeyboardInterrupt, EOFError):
                try:
                    # TODO(albert): When you use Ctrl+C in Windows, it
                    # throws two exceptions, so you need to catch both
                    # of them. Find a cleaner fix for this.
                    print()
                except (KeyboardInterrupt, EOFError):
                    pass
                raise UnlockException
            if student_input in self.EXIT_INPUTS:
                raise UnlockException

            self._add_line_to_history(student_input)

            if output.choices:
                student_input = choice_map[student_input]
            correct = verify_fn(student_input, output.answer)
            if not correct:
                print("-- Not quite. Try again! --")
        return student_input

    def _add_line_to_history(self, line):
        """Adds the given line to readline history, only if the line
        is non-empty.
        """
        if line:
            readline.add_history(line)
