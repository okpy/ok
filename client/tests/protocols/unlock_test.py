"""Tests the UnlockProtocol."""

from client.models import core
from client.protocols import unlock
from client.utils import output
from unittest import mock
import unittest

class InteractTest(unittest.TestCase):
    EXIT = unlock.UnlockConsole.EXIT_INPUTS[0]
    ANSWER = '42'

    def setUp(self):
        mock_verify = lambda x, y: self.encode(x) == y
        self.logger = output.OutputLogger()
        self.console = unlock.UnlockConsole(self.logger, '', analytics={'current':'q1', 'q1': []})
        self.console._verify = mock.Mock(side_effect=mock_verify)
        self.register_choices()

    def calls_interact(self, expect_answer, locked_answer,
            choices=None, aborts=False):
        if aborts:
            self.assertRaises(unlock.UnlockException,
                    self.console._interact, locked_answer, choices)
        else:
            answer = self.console._interact(locked_answer, choices)
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

    def check_analytics(self, expected):
        self.assertEqual(self.console._analytics['q1'][-1], expected)

    def encode(self, text):
        return '---' + text

    def testSuccessOnFirstTry(self):
        self.register_input(self.ANSWER, self.EXIT)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER))
        self.check_analytics((1, True))

    def testRun_codeFailedFirstTry(self):
        self.register_input('9', self.ANSWER, self.EXIT)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER))
        self.check_analytics((2, True))

    def testRun_codeNeverPasses(self):
        self.register_input('9', '2', '3', self.EXIT)
        self.calls_interact(self.ANSWER, self.encode(self.ANSWER),
                aborts=True)
        self.check_analytics((3, False))

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
        self.logger = output.OutputLogger()
        self.mock_test = core.Test(names=['dummy'], points=1)

    def makeUnlockTestCase(self, lock=True, abort=False):
        case = unlock.UnlockTestCase(type=unlock.UnlockTestCase.type,
                                     locked=lock)
        if abort:
            case.on_unlock = mock.Mock(
                    side_effect=unlock.UnlockException)
        else:
            case.on_unlock = mock.Mock(return_value=[])
        return case

    def calls_unlock(self, test, expected_unlocked):
        cases_unlocked = unlock.unlock(test, self.logger, '')[0]
        self.assertEqual(expected_unlocked, cases_unlocked)

    def testNoSuites(self):
        self.calls_unlock(self.mock_test, 0)

    def testOneSuite_noUnlockTestCase(self):
        self.mock_test.add_suite([
            core.TestCase(type=core.TestCase.type)
        ])
        self.calls_unlock(self.mock_test, 0)

    def testOneSuite_pass(self):
        self.mock_test.add_suite([
            self.makeUnlockTestCase(),
            self.makeUnlockTestCase()
        ])
        self.calls_unlock(self.mock_test, 2)

    def testOneSuite_secondCaseFail(self):
        self.mock_test.add_suite([
            self.makeUnlockTestCase(),
            self.makeUnlockTestCase(abort=True)
        ])
        self.calls_unlock(self.mock_test, 1)

    def testOneSuite_firstCaseFail(self):
        self.mock_test.add_suite([
            self.makeUnlockTestCase(abort=True),
            self.makeUnlockTestCase(abort=False)
        ])
        self.calls_unlock(self.mock_test, 0)

    def testTwoSuites_pass(self):
        self.mock_test.add_suite([
            self.makeUnlockTestCase(),
            self.makeUnlockTestCase()
        ])
        self.mock_test.add_suite([
            self.makeUnlockTestCase()
        ])
        self.calls_unlock(self.mock_test, 3)

    def testTwoSuites_secondSuiteFail(self):
        self.mock_test.add_suite([
            self.makeUnlockTestCase(),
            self.makeUnlockTestCase()
        ])
        self.mock_test.add_suite([
            self.makeUnlockTestCase(abort=True)
        ])
        self.calls_unlock(self.mock_test, 2)

    def testTwoSuites_firstSuiteFail(self):
        self.mock_test.add_suite([
            self.makeUnlockTestCase(abort=True)
        ])
        self.mock_test.add_suite([
            self.makeUnlockTestCase()
        ])
        self.calls_unlock(self.mock_test, 0)

    def testTwoSuites_withUnlockedTest(self):
        self.mock_test.add_suite([
            self.makeUnlockTestCase(lock=False),
            self.makeUnlockTestCase()
        ])
        self.mock_test.add_suite([
            self.makeUnlockTestCase()
        ])
        self.calls_unlock(self.mock_test, 2)

class LockTest(unittest.TestCase):
    def setUp(self):
        self.args = mock.Mock()
        self.args.lock = True
        self.assignment = core.Assignment.deserialize({
            'name': 'dummy',
            'version': '1.0',
        }, {})
        self.logger = mock.Mock()
        self.proto = unlock.LockProtocol(self.args, self.assignment,
                                         self.logger)

        self.test = core.Test(names=['dummy'], points=1)
        self.mock_case = MockUnlockCase(type='dummy')
        self.mock_case.on_unlock = mock.Mock()
        self.mock_case.on_lock = mock.Mock()
        self.test.add_suite([self.mock_case])
        self.assignment.add_test(self.test)

    def testNotYetLocked(self):
        # TestCase starts as unlocked.
        self.mock_case['locked'] = False
        self.proto.on_start()
        self.assertTrue(self.mock_case.on_lock.called)
        self.mock_case.on_lock.assert_called_with(self.proto._hash_fn)

    def testAlreadyLocked(self):
        self.mock_case['locked'] = True
        self.proto.on_start()
        self.assertFalse(self.mock_case.on_lock.called)

    def testNeverLock(self):
        self.mock_case['never_lock'] = True
        self.proto.on_start()
        self.assertFalse(self.mock_case.on_lock.called)

    def testHiddenTest(self):
        self.mock_case['hidden'] = True
        self.proto.on_start()
        self.assertFalse(self.mock_case.on_lock.called)
        self.assertEqual(0, self.test.num_cases)

    def testHiddenParamsInTest(self):
        self.test['hidden_params'] = {
            'foo': 'bar'
        }
        self.proto.on_start()
        self.assertEqual({}, self.test['hidden_params'])

    def testHiddenParamsInAssignment(self):
        self.assignment['hidden_params'] = {
            'foo': 'bar'
        }
        self.proto.on_start()
        self.assertEqual({}, self.test['hidden_params'])

class MockUnlockCase(unlock.UnlockTestCase):
    def on_onlock(self, logger, interact_fn):
        pass

    def on_lock(self, hash_fn):
        pass
