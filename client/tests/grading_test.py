import sys
import time
import unittest
from utils import OutputLogger, TIMEOUT
from grading import TestingConsole, run, TestCaseAnswer

class TestingConsoleTest(unittest.TestCase):
    def setUp(self):
        self.logger = OutputLogger()
        self.console = TestingConsole(self.logger)

    #############
    # Test exec #
    #############

    def execTest(self, expr, should_error, expected=None, frame=None):
        if frame is None:
            frame = {}
        errored = self.console.exec(expr, frame, expected=expected)
        if should_error:
            self.assertTrue(errored)
        else:
            self.assertFalse(errored)

    def testExec_expectedWithNoErrors(self):
        self.execTest("x + 4", False, '7', {'x': 3})

    def testExec_expectedWithNoEqualsError(self):
        self.execTest("2 + 4", True, '7')

    def testExec_expectedExceptionWithNoError(self):
        self.execTest("1 / 0", False, 'ZeroDivisionError')

    def testExec_expectedExceptionWithNotEqualsError(self):
        self.execTest("1 + 2", True, 'ZeroDivisionError')

    def testExec_expectedExceptionWithWrongException(self):
        self.execTest("1 / 0", True, 'TypeError')

    def testExec_runtimeError(self):
        max_recursion = lambda: max_recursion()
        self.execTest("f()", True, frame={'f': max_recursion})

    def testExec_timeoutError(self):
        # TODO(albert): have a better way to test timeout than actually
        # waiting.
        def wait():
            time.sleep(TIMEOUT * 3 // 2)
        self.execTest("f()", True, frame={'f': wait})

    ############
    # Test run #
    ############

    def runTest(self, test_case, expected_log, errored, frame=None):
        if frame is None:
            frame = {}
        error, log = self.console.run(test_case, frame)
        if errored:
            self.assertTrue(error)
        else:
            self.assertFalse(error)
        self.assertEqual(expected_log, log)

    def testRun_basicLog(self):
        self.runTest(MockTestCase(
            lines=[
                '$ x + 2',
            ],
            outputs=[
                '4',
            ],
        ), [
            '>>> x + 2', '\n',
            '4', '\n',
        ], False, frame={'x':2})

    def testRun_basicLogNoFrame(self):
        self.runTest(MockTestCase(
            lines=[
                '$ 2 + 2',
            ],
            outputs=[
                '4',
            ],
        ), [
            '>>> 2 + 2', '\n',
            '4', '\n',
        ], False)

    def testRun_indentNoNewline(self):
        self.runTest(MockTestCase(
            lines=[
                'def square(x):',
                '    return x * x',
                '$ square(4)',
            ],
            outputs=[
                '16',
            ],
        ), [
            '>>> def square(x):', '\n',
            '...     return x * x', '\n',
            '>>> square(4)', '\n',
            '16', '\n',
        ], False)

    def testRun_indentWithNewline(self):
        self.runTest(MockTestCase(
            lines=[
                'def square(x):',
                '    return x * x',
                '',
                '$ square(4)',
            ],
            outputs=[
                '16',
            ],
        ), [
            '>>> def square(x):', '\n',
            '...     return x * x', '\n',
            '>>> square(4)', '\n',
            '16', '\n',
        ], False)

    def testRun_forLoop(self):
        self.runTest(MockTestCase(
            lines=[
                'for i in range(3):',
                '    print(i)',
                '$ 3 + 4',
            ],
            outputs=[
                '7',
            ],
        ), [
            '>>> for i in range(3):', '\n',
            '...     print(i)', '\n',
            '0', '\n',
            '1', '\n',
            '2', '\n',
            '>>> 3 + 4', '\n',
            '7', '\n',
        ], False)

    def testRun_failedPrompt(self):
        self.runTest(MockTestCase(
            lines=[
                '$ 3 + 4',
            ],
            outputs=[
                '2',
            ],
        ), [
            '>>> 3 + 4', '\n',
            '7', '\n',
            '# Error: expected 2 got 7', '\n',
        ], True)

    def testRun_failedNonPrompt(self):
        self.runTest(MockTestCase(
            lines=[
                '1 / 0',
                '$ 3 + 4',
            ],
            outputs=[
                '7',
            ],
        ), [
            '>>> 1 / 0', '\n',
            'Traceback (most recent call last):', '\n',
            'ZeroDivisionError: division by zero\n', '\n',
        ], True)

    def testRun_failedPromptWithException(self):
        self.runTest(MockTestCase(
            lines=[
                '$ 1 / 0',
            ],
            outputs=[
                '7',
            ],
        ), [
            '>>> 1 / 0', '\n',
            'Traceback (most recent call last):', '\n',
            "ZeroDivisionError: division by zero\n", '\n',
            '# Error: expected 7 got ZeroDivisionError', '\n',
        ], True)

class RunTest(unittest.TestCase):
    def setUp(self):
        self.logger = OutputLogger()
        self.console = TestingConsole(self.logger)

    def testRun_noSuites(self):
        test = MockTest()
        passed, total = run(test, {}, self.console)
        self.assertEqual(0, passed)
        self.assertEqual(0, total)

    def testRun_oneTestCasePass(self):
        test = MockTest(suites=[
            [
                MockTestCase(lines=[
                    '$ 3 + 4',
                ],
                outputs=[
                    '7'
                ]),
            ],
        ])
        passed, total = run(test, {}, self.console)
        self.assertEqual(1, passed)
        self.assertEqual(1, total)

    def testRun_multipleTestCaseOneSuitePass(self):
        test = MockTest(suites=[
            [
                MockTestCase(lines=[
                    '$ 3 + 4',
                ],
                outputs=[
                    '7'
                ]),
                MockTestCase(lines=[
                    'def square(x):',
                    '    return x * x',
                    '$ square(4)',
                ],
                outputs=[
                    '16'
                ]),
            ],
        ])
        passed, total = run(test, {}, self.console)
        self.assertEqual(2, passed)
        self.assertEqual(2, total)

    def testRun_multipleSuitesPass(self):
        test = MockTest(suites=[
            [
                MockTestCase(lines=[
                    '$ 3 + 4',
                ],
                outputs=[
                    '7'
                ]),
                MockTestCase(lines=[
                    'def square(x):',
                    '    return x * x',
                    '$ square(4)',
                ],
                outputs=[
                    '16'
                ]),
            ],
            [
                MockTestCase(lines=[
                    '$ 5 + 2',
                ],
                outputs=[
                    '7'
                ]),
                MockTestCase(lines=[
                    '$ 1 / 0',
                ],
                outputs=[
                    'ZeroDivisionError'
                ]),
            ],
        ])
        passed, total = run(test, {}, self.console)
        self.assertEqual(4, passed)
        self.assertEqual(4, total)

    def testRun_singleTestCaseFail(self):
        test = MockTest(suites=[
            [
                MockTestCase(lines=[
                    '$ 1 / 0',
                ],
                outputs=[
                    '7'
                ]),
            ],
        ])
        passed, total = run(test, {}, self.console)
        self.assertEqual(0, passed)
        self.assertEqual(1, total)

    def testRun_singleSuiteSecondTestCaseFail(self):
        test = MockTest(suites=[
            [
                MockTestCase(lines=[
                    '$ 4 + 3',
                ],
                outputs=[
                    '7'
                ]),
                MockTestCase(lines=[
                    '$ 1 / 0',
                ],
                outputs=[
                    '7'
                ]),
            ],
        ])
        passed, total = run(test, {}, self.console)
        self.assertEqual(1, passed)
        self.assertEqual(2, total)

    def testRun_multipleSuitesFirstSuiteFail(self):
        test = MockTest(suites=[
            [
                MockTestCase(lines=[
                    '$ 1 / 0',
                ],
                outputs=[
                    '7'
                ]),
            ],
            [
                MockTestCase(lines=[
                    '$ 3 + 4',
                ],
                outputs=[
                    '7'
                ]),
            ],
        ])
        passed, total = run(test, {}, self.console)
        self.assertEqual(0, passed)
        self.assertEqual(1, total)

    def testRun_teardownExecutionNoFailure(self):
        lst = []
        test = MockTest(suites=[
            [
                MockTestCase(lines=[
                    '$ 3 + 4',
                ],
                outputs=[
                    '7'
                ],
                teardown="f()"),
            ],
        ])
        passed, total = run(test, {'f': lambda: lst.append(1)},
                self.console)
        self.assertEqual(1, passed)
        self.assertEqual(1, total)
        self.assertEqual([1], lst)

    def testRun_teardownExecutionWithFailure(self):
        lst = []
        test = MockTest(suites=[
            [
                MockTestCase(lines=[
                    '$ 1 / 0',
                ],
                outputs=[
                    '7'
                ],
                teardown="f()"),
            ],
        ])
        passed, total = run(test, {'f': lambda: lst.append(1)},
                self.console)
        self.assertEqual(0, passed)
        self.assertEqual(1, total)
        self.assertEqual([1], lst)

    def testRun_abortLockedTests(self):
        lst = []
        test = MockTest(suites=[
            [
                MockTestCase(lines=[
                    '$ 1 / 0',
                ],
                outputs=[
                    '7'
                ],
                status = {
                    'lock': True,
                }),
                # This TestCase should never be run.
                MockTestCase(lines=[
                    '$ 4 + 3',
                ],
                outputs=[
                    '7'
                ]),
            ],
        ])
        passed, total = run(test, {}, self.console)
        self.assertEqual(0, passed)
        self.assertEqual(1, total)  # The locked test is not counted.

    def testRun_conceptTestCaseNotCounted(self):
        lst = []
        test = MockTest(suites=[
            [
                # This TestCase should not be included in score.
                MockTestCase(lines=[
                    'This is a concept question.',
                ],
                outputs=[
                    '7'
                ],
                status = {
                    'concept': True,
                }),
                MockTestCase(lines=[
                    '$ 4 + 3',
                ],
                outputs=[
                    '7'
                ]),
            ],
        ])
        passed, total = run(test, {}, self.console)
        self.assertEqual(1, passed)
        self.assertEqual(1, total)


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
    def __init__(self, lines=None, outputs=None, status=None,
            q_type=None, teardown=None):
        self.lines = lines or []
        if not outputs:
            self.outputs = []
        else:
            self.outputs = [TestCaseAnswer(out) for out in outputs]
        self.status = status or {}
        self.type = q_type or ''
        self.teardown = teardown or ''

    @property
    def is_graded(self):
        return not self.is_locked and not self.is_conceptual

    @property
    def is_locked(self):
        return self.status.get('lock', False)

    @property
    def is_conceptual(self):
        return self.status.get('concept', False)



