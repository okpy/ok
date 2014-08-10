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

    def runTest(self, input_case, output_case=None):
        if not output_case:
            output_case = input_case.copy()
        self.console.run(input_case)    # Modifies input_case.
        self.assertCaseEqual(output_case, input_case)

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
        ]))

    def testRun_codeEOFError(self):
        self.register_input(EOFError)
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), MockTestCase(outputs=[
            TestCaseAnswer(self.encode('7')),
        ]))

    def testRun_codeKeyboardInterrupt(self):
        self.register_input(KeyboardInterrupt)
        self.runTest(MockTestCase(lines=[
            '$ 3 + 4',
        ], outputs=[
            TestCaseAnswer(self.encode('7')),
        ]), MockTestCase(outputs=[
            TestCaseAnswer(self.encode('7')),
        ]))

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
        ], locked=True))

    def testRun_codeMultipleChoice(self):
        self.register_choices()
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
        self.register_choices()
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
