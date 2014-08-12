import sys
import time
import unittest
from grading import TestCaseAnswer
from unlock import UnlockConsole, unlock
from utils import OutputLogger

class UnlockConsoleTest(unittest.TestCase):
    def setUp(self):
        self.logger = OutputLogger()
        verify = lambda x, y: self.encode(x) == y
        self.console = UnlockConsole(self.logger, verify)
        self.register_choices()

    def register_input(self, *student_input):
        input_num = 0
        def get_input(prompt):
            nonlocal input_num
            input = student_input[input_num]
            if input_num < len(student_input) - 1:
                input_num += 1
            if type(input) == type and issubclass(input, BaseException):
                raise input
            return input
        self.console._input = get_input

    def register_choices(self):
        def display_choices(choices):
            return {str(i): choice for i, choice in enumerate(choices)}
        self.console._display_choices = display_choices

    def encode(self, text):
        return '---' + text

    def assertCaseEqual(self, expected, actual):
        self.assertEqual(expected.status, actual.status)
        for e_out, a_out in zip(expected.outputs, actual.outputs):
            self.assertEqual(e_out.answer, a_out.answer)
            self.assertEqual(e_out.choices, a_out.choices)

    ###################
    # Test run method #
    ###################

    def runTest(self, in_case, out_case=None, should_error=False):
        if not out_case:
            out_case = input_case.copy()
        error = self.console.run(in_case)    # Modifies input_case.
        if should_error:
            self.assertTrue(error)
        else:
            self.assertFalse(error)
        self.assertCaseEqual(out_case, in_case)

    def testRun_codeSinglePromptSuccess(self):
        self.register_input('7', 'exit()')
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), MockTestCase(outputs=[
            TestCaseAnswer('7')
        ], locked=False))

    def testRun_codeFailedFirstTry(self):
        self.register_input('9', '7', 'exit()')
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), MockTestCase(outputs=[
            TestCaseAnswer('7')
        ], locked=False))

    def testRun_codeAbort(self):
        self.register_input('exit()')
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), MockTestCase(outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), should_error=True)

    def testRun_codeEOFError(self):
        self.register_input(EOFError)
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), MockTestCase(outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), should_error=True)

    def testRun_codeKeyboardInterrupt(self):
        self.register_input(KeyboardInterrupt)
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), MockTestCase(outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), should_error=True)

    def testRun_codeMultiPromptCorrect(self):
        self.register_input('7', '6', 'exit()')
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
            '$ 2 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7')),
            TestCaseAnswer(self.encode('6')),
        ]), MockTestCase(outputs=[
            TestCaseAnswer('7'),
            TestCaseAnswer('6'),
        ], locked=False))

    def testRun_codeMultiPromptHalfCorrect(self):
        self.register_input('7', '2', 'exit()')
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
            '$ 2 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7')),
            TestCaseAnswer(self.encode('6')),
        ]), MockTestCase(outputs=[
            TestCaseAnswer(self.encode('7')),
            TestCaseAnswer(self.encode('6')),
        ], locked=True),
        should_error=True)

    def testRun_codeMultipleChoice(self):
        self.register_input('1', 'exit()')
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7'),
                choices=['6', '7', '3']),
        ]), MockTestCase(outputs=[
            TestCaseAnswer('7'),
        ], locked=False))

    def testRun_concept(self):
        self.register_input('1', 'exit()')
        self.runTest(MockTestCase(lines=[
            '$ These dollar signs',
            '$ should not be treated as prompts',
            '$ since this is a concept question',
        ], outputs=[
            TestCaseAnswer(self.encode('7'),
                choices=['6', '7', '3']),
        ], concept=True), MockTestCase(outputs=[
            TestCaseAnswer('7'),
        ], locked=False, concept=True))

class UnlockTest(unittest.TestCase):
    def setUp(self):
        self.console = MockUnlockConsole()

    def unlockTest(self, test, expected_unlocked):
        cases_unlocked = unlock(test, self.console)
        self.assertEqual(expected_unlocked, cases_unlocked)

    def testNoSuites(self):
        test = MockTest()
        self.unlockTest(test, 0)

    def testOneSuite_success(self):
        test = MockTest(suites=[
            [MockTestCase(),
             MockTestCase()]
        ])
        self.console.when_run_return(False)
        self.unlockTest(test, 2)

    def testOneSuite_onePassOneFail(self):
        test = MockTest(suites=[
            [MockTestCase(),
             MockTestCase()]
        ])
        self.console.when_run_return(False, True)
        self.unlockTest(test, 1)

    def testOneSuite_allFail(self):
        test = MockTest(suites=[
            [MockTestCase(),
             MockTestCase()]
        ])
        self.console.when_run_return(True)
        self.unlockTest(test, 0)

    def testTwoSuites_success(self):
        test = MockTest(suites=[
            [MockTestCase(),
             MockTestCase()],
            [MockTestCase()]
        ])
        self.console.when_run_return(False)
        self.unlockTest(test, 3)

    def testTwoSuites_halfSuccess(self):
        test = MockTest(suites=[
            [MockTestCase(),
             MockTestCase()],
            [MockTestCase()]
        ])
        self.console.when_run_return(False, False, True)
        self.unlockTest(test, 2)

    def testTwoSuites_fail(self):
        test = MockTest(suites=[
            [MockTestCase(),
             MockTestCase()],
            [MockTestCase()]
        ])
        self.console.when_run_return(True)
        self.unlockTest(test, 0)

    def testTwoSuites_withUnlockedTests(self):
        test = MockTest(suites=[
            [MockTestCase(locked=False),
             MockTestCase()],
            [MockTestCase()]
        ])
        self.console.when_run_return(False)
        self.unlockTest(test, 2)

#########
# Mocks #
#########

class MockTest:
    def __init__(self, suites=None, names=None, points=0, note='',
            cache=''):
        self.suites = suites or []
        self.names = names or ['MockTest']
        self.points = points
        self.note = note
        self.cache = cache

    @property
    def name(self):
        return self.names[0]

class MockTestCase:
    def __init__(self, lines=None, outputs=None, locked=True,
            concept=False, **kargs):
        self.lines = lines or []
        self.outputs = outputs or []
        self.status = {'lock': locked, 'concept': concept}
        self.kargs = kargs

    @property
    def is_graded(self):
        return not self.is_locked and not self.is_conceptual

    @property
    def is_locked(self):
        return self.status.get('lock', True)

    @property
    def is_conceptual(self):
        return self.status.get('concept', False)

    def set_outputs(self, new_outputs):
        self.outputs = new_outputs

    def unlock(self):
        self.status['lock'] = False

    def __eq__(self, other):
        return (isinstance(other, MockTestCase) \
                or isinstance(other, TestCase)) \
                and other.status == self.status \
                and other.outputs == self.outputs

class MockUnlockConsole:
    def __init__(self):
        self.errors = [False]
        self.counter = 0

    def when_run_return(self, *errors):
        self.errors = errors
        self.counter = 0

    def run(self, case):
        error = self.errors[self.counter]
        if self.counter < len(self.errors) - 1:
            self.counter += 1
        return error

