import random
import readline
import utils
from models import core

#######################
# UNLOCKING MECHANISM #
#######################

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
    def on_unlock(self, logger):
        """Subclasses that are used by the unlocking protocol should
        implement this method.

        RETURNS:
        list; a list of unlocked answers for a TestCase.
        """
        raise NotImplementedError


def unlock(test, logger):
    """Unlocks TestCases for a given Test.

    PARAMETERS:
    test    -- Test; the test to unlock.
    console -- UnlockConsole; a console for handling interactive
               unlocking sessions.

    DESCRIPTION:
    This function incrementally unlocks all TestCases in a specified
    Test. Students must answer in the order that TestCases are
    written. Once a TestCase is unlocked, it will remain unlocked.

    RETURN:
    int; the number of cases that are newly unlocked for this Test
    after going through an unlocking session.
    """
    # TODO(albert): move printing outside of this function
    if not test.suites:
        print('No tests to unlock for {}.'.format(test.name))
        return 0

    utils.underline('Unlocking tests for {}'.format(test.name))
    print('At each "{}", type in what you would expect the output to '
          'be if you had implemented {}'.format(UnlockConsole.PROMPT,
              test.name))
    print('Type {} to quit'.format(UnlockConsole.EXIT_INPUTS[0]))
    print()

    console = UnlockConsole(logger)
    cases = 0
    cases_unlocked = 0
    for suite_num, suite in enumerate(test.suites):
        for case_num, case in enumerate(suite):
            cases += 1
            if not case.is_locked:
                continue
            utils.underline('Case {}'.format(cases), line='-')
            if console.run(case):   # Abort unlocking.
                return cases_unlocked
            cases_unlocked += 1
    print("You are done unlocking tests for this question!")
    return cases_unlocked

class UnlockException(BaseException):
    pass

class UnlockConsole(utils.OkConsole):
    """Handles an interactive session for unlocking a TestCase.

    An instance of this class can be (and should be) reused for
    multiple TestCases. This class keeps an output log that is
    registered with the OutputLogger class, but is currently not
    used.
    """
    PROMPT = '? '       # Prompt that is used for user input.
    EXIT_INPUTS = (     # Valid user inputs for aborting the session.
        'exit()',
        'quit()',
    )

    def __init__(self, logger):
        """Constructor.

        PARAMETERS:
        logger          -- OutputLogger
        verification_fn -- function; takes as arguments
                           (student_input, locked_answer) and verifies
                           that the student_input matches the
                           locked_answer.
        """
        super().__init__(logger)

    ##################
    # Public methods #
    ##################

    def run(self, case):
        """Runs an interactive session for unlocking a single TestCase.

        PARAMETERS:
        case -- TestCase

        DESCRIPTION:
        Upon successful completion, the provided TestCase will be
        modified to contain the unlocked TestCaseAnswer, and the
        TestCase will be marked as unlocked. If the user aborts before
        successful completion, the TestCase will left untouched.

        RETURNS:
        bool; True if an error/abort occurs, False if the TestCase is
        unlocked successfully.
        """
        self._activate_logger()

        try:
            answers = case.on_unlock(self.interact)
        except UnlockException:
            print('\nExiting unlocker...')
            return True
        else:
            case.set_outputs(answers)
            case.set_locked(False)
            print("-- Congratulations, you unlocked this case! --")
            print()
            return False
        finally:
            self._deactivate_logger()

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

    # TODO(albert): move to ConceptTestCase
    def __run_concept(self, case):
        """Runs an unlocking session for a conceptual TestCase."""
        print('\n'.join(case.lines))
        answer = self.interact(case.outputs[0])
        return [core.TestCaseAnswer(answer)]

    def interact(self, output, verify_fn):
        """Reads student input for unlocking tests until the student
        answers correctly.

        PARAMETERS:
        output  -- TestCaseAnswer; a locked test case answer.

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
