import random
from utils import underline, maybe_strip_prompt, OkConsole

#######################
# UNLOCKING MECHANISM #
#######################

def __make_hash_fn(hash_key, encoding='utf-8'):
    def hash_fn(x):
        return hmac.new(hash_key.encode(encoding),
                        x.encode(encoding)).digest()
    return hash_fn

hash_key = tests['project_info']['hash_key']
__make_hash_fn(hash_key)

def unlock(test, console, hash_fn):
    """Unlocks TestCases for a given Test.

    PARAMETERS:
    test -- Test; the test to unlock.

    DESCRIPTION:
    This function incrementally unlocks all TestCases in a specified
    Test. Students must answer in the order that TestCases are
    written. Once a TestCase is unlocked, it will remain unlocked.

    Persistant state is stored by rewriting the contents of
    tests.pkl. Students should NOT manually change these files.
    """
    name = test.name

    if not test.suites:
        print('No tests to unlock for {}.'.format(name))
        return

    underline('Unlocking tests for {}'.format(name))
    print('At each "{}", type in what you would expect the output to '
          'be if you had implemented {}'.format(UnlockConsole.PROMPT,
              name))
    print('Type exit() to quit')
    print()

    cases = 0
    for suite_num, suite in enumerate(test.suites):
        for case_num, case in enumerate(suite):
            if not case.is_conceptual:
                # TODO(albert): consider rethinking TestCase counting.
                cases += 1
            if not case.is_locked:
                continue
            underline('Case {}'.format(cases), under='-')
            console.run(case)
    print("You are done unlocking tests for this question!")

class UnlockException(BaseException):
    pass

class UnlockConsole(OkConsole):
    PROMPT = '? '
    EXIT_INPUTS = (
        'exit()',
        'quit()',
    )

    def __init__(self, logger, verification_fn):
        super().__init__(logger)
        self.verify = verification_fn

    def run(self, case):
        self._activate_logger()

        try:
            if case.is_conceptual:
                answers = self.__run_code(case)
            else:
                answers = self.__run_concept(case)
        except UnlockException:
            print('\nExiting unlocker...')
        else:
            case.set_outputs(answers)
            case.unlock()
            print("-- Congratulations, you have unlocked this case! --")
            print()

        self._deactivate_logger()

    def __run_code(self, case):
        outputs = iter(case.outputs)
        answers = []
        for line in case.lines:
            if line.startswith(' '):  # Line is indented.
                print(PS2 + line)
                continue
            line = maybe_strip_prompt(line)
            print(PS1 + line)
            # TODO(albert): handle choices.
            answer = self.interact(next(outputs))
            answers.append(answer)
        return answers

    def __run_concept(self, case):
        print('\n'.join(case.lines))
        # TODO(albert): handle choices.
        answer = self.interact(case[1][0])
        return [answer]

    def interact(self, expected, choices=None):
        """Reads student input for unlocking tests.

        PARAMETERS:
        output  -- str; the hashed version of the correct output.
        choices -- list; sequence of choices (strings) from which
                   the student can choose

        DESCRIPTION:
        Continually prompt the student for an answer to an unlocking
        question until one of the folliwng happens:

            1. The student supplies the correct answer, in which case
               the supplied answer is returned
            2. The student aborts abnormally (either by typing 'exit()'
               or using Ctrl-C/D. In this case, return None

        Correctness is determined by hashing student input and
        comparing to the parameter "output", which is a hashed version
        of the correct answer. If the hashes are equal, the student
        answer is assumed to be correct.

        RETURNS:
        str  -- the correct solution (that the student supplied)
        """
        correct = False
        while not correct:
            if choices:
                # TODO(albert): have better format for multiple
                # choice.
                print("Choose the number of the correct choice:")
                for i, choice in enumerate(random.sample(output, len(choices))):
                    print('    ' + str(i) + ') ' + split(choice, join_str='\n       '))
                    if choice == output[0]:
                        answer = hash_fn(str(i))
            try:
                student_input = input(prompt + ' ')
            except (KeyboardInterrupt, EOFError):
                try:
                    # TODO(albert): When you use Ctrl+C in Windows, it
                    # throws two exceptions, so you need to catch both
                    # of them. Find a cleaner fix for this.
                except (KeyboardInterrupt, EOFError):
                    pass
                raise UnlockException
            if student_input in EXIT_INPUTS:
                raise UnlockException

            self.__add_line_to_history(student_input)
            correct = self.verify(student_input, answer)
            if not correct:
                print("-- Not quite. Try again! --")
        return student_input

    @staticmethod
    def __add_line_to_history(line):
        """Adds the given line to readline history, only if the line
        is non-empty.
        """
        if line:
            readline.add_history(line)
