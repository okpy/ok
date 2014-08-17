from models import core
from protocols import unlock
from unittest import mock
import unittest
import utils

class InteractTest(unittest.TestCase):
    EXIT = unlock.UnlockConsole.EXIT_INPUTS[0]
    ANSWER = '42'

    def setUp(self):
        self.logger = utils.OutputLogger()
        self.console = unlock.UnlockConsole()
        self.verify = lambda x, y: self.encode(x) == y
        self.register_choices()

    def calls_interact(self, expect_answer, locked_answer,
            choices=None, aborts=False, verify_fn=None):
        verify_fn = verify_fn or self.verify
        output = core.TestCaseAnswer(locked_answer, choices)

        if aborts:
            self.assertRaises(unlock.UnlockException,
                    self.console.interact, output, verify_fn)
        else:
            answer = self.console.interact(output, verify_fn)
            self.assertEqual(expect_answer, answer)

    def register_input(self, *student_input):
        input_num = 0
        def get_input(prompt):
            nonlocal input_num
            input_ = student_input[input_num]
            print(input_)   # Display for debugging purposes.
            if input_num < len(student_input) - 1:
                input_num += 1
            if type(input_) == type and \
                    issubclass(input_, BaseException):
                raise input_
            return input_
        self.console._input = get_input

    def register_choices(self):
        def display_choices(choices):
            return {str(i): choice for i, choice in enumerate(choices)}
        self.console._display_choices = display_choices

    def encode(self, text):
        return '---' + text

    def testSuccessOnFirstTry(self):
        self.register_input(self.ANSWER, self.EXIT)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER))

    def testRun_codeFailedFirstTry(self):
        self.register_input('9', self.ANSWER, self.EXIT)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER))

    def testAbort_exitInput(self):
        self.register_input(self.EXIT)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER),
                aborts=True)

    def testAbort_EOFError(self):
        self.register_input(EOFError)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER),
                aborts=True)

    def testAbort_KeyboardInterrupt(self):
        self.register_input(KeyboardInterrupt)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER),
                aborts=True)

    def testMultipleChoice_immediatePass(self):
        self.register_input('1', self.EXIT)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER),
                choices=['6', self.ANSWER, '3'])

    def testMultipleChoice_failOnFirstTry(self):
        self.register_input('0', '1', self.EXIT)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER),
                choices=['6', self.ANSWER, '3'])

class UnlockTest(unittest.TestCase):
    def setUp(self):
        self.logger = utils.OutputLogger()

    def makeUnlockTestCase(self, abort=False, input_str='',
            outputs=None, answers=None, **kargs):
        case = unlock.UnlockTestCase(input_str, outputs or [], **kargs)
        if abort:
            case.on_unlock = mock.Mock(
                    side_effect=unlock.UnlockException)
        else:
            case.on_unlock = mock.Mock(return_value=answers or [])
        return case

    def makeTestCase(self, input_str='', outputs=None, lock=False,
            **kargs):
        case = core.TestCase(input_str, outputs or [], lock=lock,
                **kargs)
        return case

    def calls_unlock(self, test, expected_unlocked):
        cases_unlocked = unlock.unlock(test, self.logger)
        self.assertEqual(expected_unlocked, cases_unlocked)

    def testNoSuites(self):
        test = core.Test()
        self.calls_unlock(test, 0)

    def testOneSuite_noUnlockTestCase(self):
        test = core.Test()
        test.add_suite([
            self.makeTestCase(),
        ])
        self.calls_unlock(test, 0)

    def testOneSuite_pass(self):
        test = core.Test()
        test.add_suite([
            self.makeUnlockTestCase(),
            self.makeUnlockTestCase()
        ])
        self.calls_unlock(test, 2)

    def testOneSuite_secondCaseFail(self):
        test = core.Test()
        test.add_suite([
            self.makeUnlockTestCase(),
            self.makeUnlockTestCase(abort=True)
        ])
        self.calls_unlock(test, 1)

    def testOneSuite_firstCaseFail(self):
        test = core.Test()
        test.add_suite([
            self.makeUnlockTestCase(abort=True),
            self.makeUnlockTestCase(abort=False)
        ])
        self.calls_unlock(test, 0)

    def testTwoSuites_pass(self):
        test = core.Test()
        test.add_suite([
            self.makeUnlockTestCase(),
            self.makeUnlockTestCase()
        ])
        test.add_suite([
            self.makeUnlockTestCase()
        ])
        self.calls_unlock(test, 3)

    def testTwoSuites_secondSuiteFail(self):
        test = core.Test()
        test.add_suite([
            self.makeUnlockTestCase(),
            self.makeUnlockTestCase()
        ])
        test.add_suite([
            self.makeUnlockTestCase(abort=True)
        ])
        self.calls_unlock(test, 2)

    def testTwoSuites_firstSuiteFail(self):
        test = core.Test()
        test.add_suite([
            self.makeUnlockTestCase(abort=True)
        ])
        test.add_suite([
            self.makeUnlockTestCase()
        ])
        self.calls_unlock(test, 0)

    def testTwoSuites_withUnlockedTest(self):
        test = core.Test()
        test.add_suite([
            self.makeUnlockTestCase(lock=False),
            self.makeUnlockTestCase()
        ])
        test.add_suite([
            self.makeUnlockTestCase()
        ])
        self.calls_unlock(test, 2)

