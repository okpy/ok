"""Tests the DoctestCase model."""

from client import exceptions
from client.models import core
from client.models import doctest_case
from client.protocols import unlock
from client.utils import formatting
from client.utils import output
from unittest import mock
import sys
import unittest

class OnGradeTest(unittest.TestCase):
    ASSIGN_NAME = 'dummy'

    def setUp(self):
        # This logger captures output and is used by the unittest,
        # it is wired to stdout.
        self.log = []
        self.capture = sys.stdout = output.OutputLogger()
        self.capture.register_log(self.log)
        self.capture.on = mock.Mock()
        self.capture.off = mock.Mock()

        # This logger is used by on_grade.
        self.logger = output.OutputLogger()

        self.case_map = {'doctest': doctest_case.DoctestCase}
        self.makeAssignment()
        self.makeTest()

    def tearDown(self):
        self.stdout = sys.__stdout__

    def makeAssignment(self, hidden_params=None, params=None):
        json = {
            'name': self.ASSIGN_NAME,
            'version': '1.0',
        }
        if hidden_params:
            json['hidden_params'] = hidden_params
        if params:
            json['params'] = params
        self.assignment = core.Assignment.deserialize(json, self.case_map)
        return self.assignment

    def makeTest(self, hidden_params=None, params=None):
        json = {
            'names': ['q1'],
            'points': 1,
        }
        if hidden_params:
            json['hidden_params'] = hidden_params
        if params:
            json['params'] = params
        self.test = core.Test.deserialize(json, self.assignment, self.case_map)
        return self.test

    def makeTestCase(self, case_json):
        case_json['type'] = doctest_case.DoctestCase.type
        if 'locked' not in case_json:
            case_json['locked'] = False
        return doctest_case.DoctestCase.deserialize(case_json,
                self.assignment, self.test)

    def calls_onGrade(self, case_json, errors=False, verbose=False,
            interact=False):
        case = self.makeTestCase(case_json)
        error = case.on_grade(self.logger, verbose, interact, 10)
        if errors:
            self.assertTrue(error)
        else:
            self.assertFalse(error)

    def assertCorrectLog(self, expected_log):
        expected_log = '\n'.join(expected_log).strip('\n')
        log = ''.join(self.capture.log).strip('\n')
        self.assertEqual(expected_log, log)

    def testPass_equals(self):
        self.calls_onGrade({
            'test': """
            >>> 3 + 4
            7
            """,
        })

    def testPass_expectException(self):
        self.calls_onGrade({
            'test': """
            >>> 1 / 0
            ZeroDivisionError
            """,
        })

    def testPass_multilineSinglePrompt(self):
        self.calls_onGrade({
            'test': """
            >>> x = 5
            >>> x + 4
            9
            """,
        })

    def testPass_multiplePrompts(self):
        self.calls_onGrade({
            'test': """
            >>> x = 5
            >>> x + 4
            9
            >>> 1 / 0
            ZeroDivisionError
            """,
        })

    def testPass_multilineWithIndentation(self):
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x
            >>> square(4)
            16
            """,
        })

    def testPass_assignmentParams(self):
        self.makeAssignment(params={
            'doctest': {
                'cache': 'x = 3',
                'setup': 'y = 1',
            }
        })
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x
            >>> square(x)
            9
            >>> square(y)
            1
            """,
        })

    def testPass_hiddenAssignmentParams(self):
        self.makeAssignment(hidden_params={
            'doctest': {
                'setup': 'y = 4',
            }
        }, params={
            'doctest': {
                'cache': 'x = 3',
                'setup': 'y = 1',
            }
        })
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x
            >>> square(x)
            9
            >>> square(y)
            16
            """,
        })

    def testPass_testParams(self):
        self.makeTest(params={
            'doctest': {
                'cache': 'x = 3',
                'setup': 'y = 1',
            }
        })
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x
            >>> square(x)
            9
            >>> square(y)
            1
            """,
        })

    def testPass_hiddenTestParams(self):
        self.makeTest(hidden_params={
            'doctest': {
                'setup': 'y = 4',
            }
        }, params={
            'doctest': {
                'cache': 'x = 3',
                'setup': 'y = 1',
            }
        })
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x
            >>> square(x)
            9
            >>> square(y)
            16
            """,
        })

    def testPass_teardown(self):
        # TODO(albert)
        pass

    def testError_notEqualError(self):
        self.calls_onGrade({
            'test': """
            >>> 2 + 4
            7
            """,
        }, errors=True)

    def testError_expectedException(self):
        self.calls_onGrade({
            'test': """
            >>> 1 + 2
            ZeroDivisionError
            """,
        }, errors=True)

    def testError_wrongException(self):
        self.calls_onGrade({
            'test': """
            >>> 1 / 0
            TypeError
            """,
        }, errors=True)

    def testError_runtimeError(self):
        self.calls_onGrade({
            'test': """
            >>> f = lambda: f()
            >>> f()
            4
            """,
        }, errors=True)

    def testError_timeoutError(self):
        # TODO(albert): test timeout errors without actually waiting
        # for timeouts.
        pass

    def testError_teardown(self):
        # TODO(albert):
        pass

    def testOutput_singleLine(self):
        self.calls_onGrade({
            'test': """
            >>> 1 + 2
            3
            """
        })
        self.assertCorrectLog([
            '>>> 1 + 2',
            '3'
        ])

    def testOutput_multiLineIndentNoNewline(self):
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x
            >>> square(4)
            16
            """,
        })
        self.assertCorrectLog([
            '>>> def square(x):',
            '...     return x * x',
            '>>> square(4)',
            '16',
        ])

    def testOutput_multiLineIndentWithNewLine(self):
        self.calls_onGrade({
            'test': """
            >>> def square(x):
            ...     return x * x

            >>> square(4)
            16
            """,
        })
        self.assertCorrectLog([
            '>>> def square(x):',
            '...     return x * x',
            '>>> square(4)',
            '16',
        ])

    def testOutput_forLoop(self):
        self.calls_onGrade({
            'test': """
            >>> for i in range(3):
            ...     print(i)
            >>> 3 + 4
            7
            """
        })
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
        self.calls_onGrade({
            'test': """
            >>> 3 + 4
            1
            """,
        }, errors=True)
        self.assertCorrectLog([
            '>>> 3 + 4',
            '7',
            '# Error: expected 1 got 7'
        ])

    def testOutput_errorOnNonPrompt(self):
        self.calls_onGrade({
            'test': """
            >>> x = 1 / 0
            >>> 3 + 4
            7
            """,
        }, errors=True)
        self.assertCorrectLog([
            '>>> x = 1 / 0',
            'ZeroDivisionError: division by zero'
        ])

    def testOutput_errorOnPromptWithException(self):
        self.calls_onGrade({
            'test': """
            >>> 1 / 0
            1
            """,
        }, errors=True)
        self.assertCorrectLog([
            '>>> 1 / 0',
            'ZeroDivisionError: division by zero',
            '# Error: expected 1 got ZeroDivisionError'
        ])

class OnUnlockTest(unittest.TestCase):
    ASSIGN_NAME = 'dummy'

    def setUp(self):
        self.assignment = core.Assignment.deserialize({
            'name': self.ASSIGN_NAME,
            'version': '1.0',
        }, {})
        self.test = core.Test.deserialize({
            'names': ['q1'],
            'points': 1,
        }, self.assignment, {})
        self.logger = mock.Mock()
        self.mock_answer = mock.Mock()
        self.interact_fn = mock.Mock(return_value=self.mock_answer)

    def makeTestCase(self, case_json):
        case_json['type'] = doctest_case.DoctestCase.type
        return doctest_case.DoctestCase.deserialize(case_json,
                self.assignment, self.test)

    def calls_onUnlock(self, case_json, expect, errors=False):
        case = self.makeTestCase(case_json)
        if errors:
            self.assertRaises(unlock.UnlockException, case.on_unlock,
                              self.logger, self.interact_fn)
            return
        case.on_unlock(self.logger, self.interact_fn)
        self.assertFalse(case['locked'])

        answers = [line for line in case.lines
                        if isinstance(line, doctest_case._Answer)]
        self.assertEqual(expect,
                         [answer.output for answer in answers])
        self.assertEqual([False] * len(answers),
                         [answer.locked for answer in answers])

    def testUnlockAll(self):
        self.calls_onUnlock({
            'test': """
            >>> 3 + 4
            <hash>
            # locked
            >>> 3 + 1
            <hash>
            # locked
            >>> 1 / 0
            <hash>
            # locked
            """,
        }, [self.mock_answer] * 3)

    def testNoLockedAnswers(self):
        self.calls_onUnlock({
            'test': """
            >>> 3 + 4
            7
            >>> 'foo'
            'foo'
            """,
        }, ['7', "'foo'"])

    def testPartiallyLockedAnswers(self):
        self.calls_onUnlock({
            'test': """
            >>> 3 + 4
            7
            >>> 'foo'
            <hash>
            # locked
            """,
        }, ['7', self.mock_answer])

class OnLockTest(unittest.TestCase):
    ASSIGN_NAME = 'dummy'
    ANSWER = 42

    def setUp(self):
        self.assignment = core.Assignment.deserialize({
            'name': self.ASSIGN_NAME,
            'version': '1.0',
        }, {})
        self.test = core.Test.deserialize({
            'names': ['q1'],
            'points': 1,
        }, self.assignment, {})
        self.hash_fn = mock.Mock(return_value=self.ANSWER)

    def makeTestCase(self, case_json):
        case_json['type'] = doctest_case.DoctestCase.type
        case_json['locked'] = True
        return doctest_case.DoctestCase.deserialize(case_json,
                self.assignment, self.test)

    def calls_onLock(self, case_json, expect):
        case = self.makeTestCase(case_json)
        case.on_lock(self.hash_fn)
        self.assertTrue(case['locked'])

        answers = [line for line in case.lines
                        if isinstance(line, doctest_case._Answer)]
        self.assertEqual(expect,
                         [answer.output for answer in answers])
        self.assertEqual([True] * len(answers),
                         [answer.locked for answer in answers])

    def testLockAll(self):
        self.calls_onLock({
            'test': """
            >>> 3 + 4
            7
            >>> 3 + 1
            4
            >>> 1 / 0
            ZeroDivisionError
            """,
        }, [self.ANSWER] * 3)

    def testLockNone(self):
        self.calls_onLock({
            'test': """
            >>> 3 + 4
            7
            # locked
            >>> 'foo'
            'foo'
            # locked
            """,
        }, ['7', "'foo'"])

    def testPartiallyLockedAnswers(self):
        self.calls_onLock({
            'test': """
            >>> 3 + 4
            7
            >>> 9
            9
            # locked
            """,
        }, [self.ANSWER, '9'])

class SerializationTest(unittest.TestCase):
    ASSIGN_NAME = 'dummy'

    def setUp(self):
        self.assignment = core.Assignment.deserialize({
            'name': self.ASSIGN_NAME,
            'version': '1.0',
        }, {})
        self.test = core.Test.deserialize({
            'names': ['q1'],
            'points': 1,
        }, self.assignment, {})

    def assertSerialize(self, json):
        case = doctest_case.DoctestCase.deserialize(
                json, self.assignment, self.test)
        self.assertEqual(json, case.serialize())

    def testIncorrectType(self):
        case_json = {'type': 'foo'}
        self.assertRaises(exceptions.DeserializeError,
                          doctest_case.DoctestCase.deserialize,
                          case_json, self.assignment, self.test)

    def testSimplePrompt(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': formatting.dedent("""
            >>> square(-2)
            4
            """),
        })

    def testExplanation(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': formatting.dedent("""
            >>> square(-2)
            4
            # explanation: Squares a negative number
            """),
        })

    def testMultipleChoice(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': formatting.dedent("""
            >>> square(-2)
            4
            # choice: 0
            # choice: 2
            # choice: -4
            """),
        })

    def testLocked(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': formatting.dedent("""
            >>> square(-2)
            5
            # locked
            """),
        })

    def testMultiplePrompts(self):
        self.assertSerialize({
            'type': 'doctest',
            'test': formatting.dedent("""
            >>> square(-2)
            4
            >>> x = 4
            >>> square(x)
            16
            """),
        })

    def testAssignmentParams(self):
        self.assignment['params'] = {
            'doctest': {
                'setup': 'x = 1',
                'teardown': 'x = 2',
                'cache': 'x = 3',
            }
        }
        self.assertSerialize({
            'type': 'doctest',
            'test': formatting.dedent("""
            >>> square(2)
            4
            """)
        })

    def testTestParams(self):
        self.test['params'] = {
            'doctest': {
                'setup': 'x = 1',
                'teardown': 'x = 2',
                'cache': 'x = 3',
            }
        }
        self.assertSerialize({
            'type': 'doctest',
            'test': formatting.dedent("""
            >>> square(2)
            4
            """)
        })
