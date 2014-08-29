"""Tests the PythonTestCase model."""

from models import core
from models import doctest_case
from unittest import mock
import ok
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

    def makeTestCase(self, input_, outputs, frame=None, teardown='',
            **status):
        frame = frame or {}
        outputs = [core.TestCaseAnswer(output) for output in outputs]
        return doctest_case.PythonTestCase(input_, outputs, frame=frame,
                test=self.test, teardown=teardown, **status)

    def calls_onGrade(self, case, errors=False, verbose=False,
            interact=False):
        error = case.on_grade(self.logger, verbose, interact)
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
        """, ['3'], frame={'f': mock_fn}, teardown='f()')

        self.calls_onGrade(case)
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
        case = self.makeTestCase('f()', ['3'],
                frame={'f': max_recursion})
        self.calls_onGrade(case, errors=True)

    # TODO(albert): test timeout errors without actually having to wait
    # for timeouts.

    def testError_teardown(self):
        mock_fn = mock.Mock()
        case = self.makeTestCase('1 + 2', ['ZeroDivisionError'],
                frame={'f': mock_fn},
                teardown='f()')

        self.calls_onGrade(case, errors=True)
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

class SerializationTest(unittest.TestCase):
    ASSIGN_NAME = 'dummy'

    def setUp(self):
        self.assignment = {'name': self.ASSIGN_NAME}

    def deserialize(self, json, assignment=None):
        assignment = assignment or self.assignment
        return doctest_case.PythonTestCase.deserialize(json, assignment)

    def testIncorrectType(self):
        case_json = {'type': 'foo'}
        self.assertRaises(core.SerializationError, self.deserialize,
                          case_json)

    def testSimplePrompt(self):
        case_json = {
            'type': 'doctest',
            'test': utils.dedent("""
            >>> square(-2)
            4
            """),
        }
        case = self.deserialize(case_json)
        self.assertEqual(['$ square(-2)'], case.lines)
        self.assertEqual(1, len(case.outputs))
        self.assertEqual('4', case.outputs[0].answer)

        self.assertEqual(case_json, case.serialize())

    def testExplanation(self):
        case_json = {
            'type': 'doctest',
            'test': utils.dedent("""
            >>> square(-2)
            4
            # explanation: Squares a negative number
            """),
        }
        case = self.deserialize(case_json)
        self.assertEqual(['$ square(-2)'], case.lines)
        self.assertEqual(1, len(case.outputs))
        self.assertEqual('4', case.outputs[0].answer)
        self.assertEqual('Squares a negative number',
                         case.outputs[0].explanation)

        self.assertEqual(case_json, case.serialize())

    def testMultipleChoice(self):
        case_json = {
            'type': 'doctest',
            'test': utils.dedent("""
            >>> square(-2)
            4
            # choice: 0
            # choice: 2
            # choice: -4
            """),
        }
        case = self.deserialize(case_json)
        self.assertEqual(['$ square(-2)'], case.lines)
        self.assertEqual(1, len(case.outputs))
        self.assertEqual('4', case.outputs[0].answer)
        self.assertEqual(['0', '2', '-4'], case.outputs[0].choices)

        self.assertEqual(case_json, case.serialize())

    def testMultiplePrompts(self):
        case_json = {
            'type': 'doctest',
            'test': utils.dedent("""
            >>> square(-2)
            4
            >>> x = 4
            >>> square(x)
            16
            """),
        }
        case = self.deserialize(case_json)
        self.assertEqual([
            '$ square(-2)',
            'x = 4',
            '$ square(x)',
        ], case.lines)
        self.assertEqual(2, len(case.outputs))
        self.assertEqual('4', case.outputs[0].answer)
        self.assertEqual('16', case.outputs[1].answer)

        self.assertEqual(case_json, case.serialize())

    # TODO(albert): test locked cases.
