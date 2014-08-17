"""Tests the PythonTestCase model."""

from models import core
from models import python
from unittest import mock
import sys
import unittest
import utils

class OnGradeTest(unittest.TestCase):
    SUITE_NUM = 0

    def setUp(self):
        # This logger captures output and is used by the unittest,
        # it is wired to stdout.
        self.log = []
        self.capture = sys.stdout = utils.OutputLogger()
        self.capture.register_log(self.log)
        self.capture.on = mock.Mock()
        self.capture.off = mock.Mock()

        # This logger is used by on_grade.
        self.logger = utils.OutputLogger()
        self.test = core.Test()

    def tearDown(self):
        self.stdout = sys.__stdout__

    def makeTestCase(self, input_, outputs, teardown='', **status):
        outputs = [core.TestCaseAnswer(output) for output in outputs]
        return python.PythonTestCase(input_, outputs, test=self.test,
                teardown=teardown, **status)

    def calls_onGrade(self, case, errors=False, frame=None,
            verbose=False, interact=False):
        frame = frame or {}
        error = case.on_grade(self.logger, frame, verbose, interact)
        if errors:
            self.assertTrue(error)
        else:
            self.assertFalse(error)

    def assertCorrectLog(self, expected_log):
        expected_log = '\n'.join(expected_log).strip('\n')
        log = ''.join(self.capture.log).strip('\n')
        self.assertEqual(expected_log, log)

    def testPass_equals(self):
        case = self.makeTestCase('3 + 4', ['7'])
        self.calls_onGrade(case)

    def testPass_expectException(self):
        case = self.makeTestCase('1 / 0', ['ZeroDivisionError'])
        self.calls_onGrade(case)

    def testPass_multilineImplicitPrompt(self):
        case = self.makeTestCase("""
        x = 5
        x + 4
        """, ['9'])
        self.calls_onGrade(case)

    def testPass_multiplePrompts(self):
        case = self.makeTestCase("""
        x = 5
        $ x + 4
        foo = 'bar'
        $ 1 / 0
        """, ['9', 'ZeroDivisionError'])
        self.calls_onGrade(case)

    def testPass_multilineWithIndentation(self):
        case = self.makeTestCase("""
        def square(x):
            return x * x
        square(4)
        """, ['16'])
        self.calls_onGrade(case)

    def testPass_teardown(self):
        mock_fn = mock.Mock()
        case = self.makeTestCase("""
        1 + 2
        """, ['3'], teardown='f()')

        self.calls_onGrade(case, frame={'f': mock_fn})
        mock_fn.assert_called_with()

    def testError_notEqualError(self):
        case = self.makeTestCase('2 + 4', ['7'])
        self.calls_onGrade(case, errors=True)

    def testError_expectedException(self):
        case = self.makeTestCase('1 + 2', ['ZeroDivisionError'])
        self.calls_onGrade(case, errors=True)

    def testError_wrongException(self):
        case = self.makeTestCase('1 / 0', ['TypeError'])
        self.calls_onGrade(case, errors=True)

    def testError_runtimeError(self):
        max_recursion = lambda: max_recursion()
        case = self.makeTestCase('f()', ['3'])
        self.calls_onGrade(case, errors=True, frame={
            'f': max_recursion,
        })

    # TODO(albert): test timeout errors without actually having to wait
    # for timeouts.

    def testError_teardown(self):
        mock_fn = mock.Mock()
        case = self.makeTestCase('1 + 2', ['ZeroDivisionError'],
                teardown='f()')

        self.calls_onGrade(case, errors=True, frame={'f': mock_fn})
        mock_fn.assert_called_with()

    def testOutput_singleLine(self):
        case = self.makeTestCase('1 + 2', ['3'])
        self.calls_onGrade(case)
        self.assertCorrectLog([
            '>>> 1 + 2',
            '3'
        ])

    def testOutput_multiLineIndentNoNewline(self):
        case = self.makeTestCase("""
        def square(x):
            return x * x
        square(4)
        """, ['16'])
        self.calls_onGrade(case)
        self.assertCorrectLog([
            '>>> def square(x):',
            '...     return x * x',
            '>>> square(4)',
            '16',
        ])

    def testOutput_multiLineIndentWithNewLine(self):
        case = self.makeTestCase("""
        def square(x):
            return x * x

        square(4)
        """, ['16'])
        self.calls_onGrade(case)
        self.assertCorrectLog([
            '>>> def square(x):',
            '...     return x * x',
            '>>> square(4)',
            '16',
        ])

    def testOutput_forLoop(self):
        case = self.makeTestCase("""
        for i in range(3):
            print(i)
        3 + 4
        """, ['7'])
        self.calls_onGrade(case)
        self.assertCorrectLog([
            '>>> for i in range(3):',
            '...     print(i)',
            '0',
            '1',
            '2',
            '>>> 3 + 4',
            '7',
        ])

    def testOutput_errorNotEqual(self):
        case = self.makeTestCase("3 + 4", ['1'])
        self.calls_onGrade(case, errors=True)
        self.assertCorrectLog([
            '>>> 3 + 4',
            '7',
            '# Error: expected 1 got 7'
        ])

    def testOutput_errorOnNonPrompt(self):
        case = self.makeTestCase("""
        1 / 0
        3 + 4
        """, ['7'])
        self.calls_onGrade(case, errors=True)
        self.assertCorrectLog([
            '>>> 1 / 0',
            'ZeroDivisionError: division by zero'
        ])

    def testOutput_errorOnPromptWithException(self):
        case = self.makeTestCase("""
        1 / 0
        """, ['1'])
        self.calls_onGrade(case, errors=True)
        self.assertCorrectLog([
            '>>> 1 / 0',
            'ZeroDivisionError: division by zero',
            '# Error: expected 1 got ZeroDivisionError'
        ])

