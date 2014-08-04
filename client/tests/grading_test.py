import sys
import time
import unittest
from utils import OutputLogger, TIMEOUT
from grading import AutograderConsole, run

class AutograderConsoleTest(unittest.TestCase):
    def setUp(self):
        self.logger = sys.stdout = OutputLogger()
        self.console = AutograderConsole(self.logger)

    def tearDown(self):
        sys.stdout = sys.__stdout__

    #############
    # Test exec #
    #############

    def execTest(self, expr, frame, expected=None, should_error=False):
        errored = self.console.exec(expr, frame, expected=expected)
        if should_error:
            self.assertTrue(errored)
        else:
            self.assertFalse(errored)

    def testExec_expectedWithNoErrors(self):
        self.execTest("x + 4", {'x': 3}, '7', False)

    def testExec_expectedWithNoEqualsError(self):
        self.execTest("2 + 4", {}, '7', True)

    def testExec_expectedExceptionWithNoError(self):
        self.execTest("1 / 0", {}, 'ZeroDivisionError', False)

    def testExec_expectedExceptionWithNotEqualsError(self):
        self.execTest("1 + 2", {}, 'ZeroDivisionError', True)

    def testExec_expectedExceptionWithWrongException(self):
        self.execTest("1 / 0", {}, 'TypeError', True)

    def testExec_runtimeError(self):
        max_recursion = lambda: max_recursion()
        self.execTest("f()", {'f': max_recursion}, should_error=True)

    def testExec_timeoutError(self):
        # TODO(albert): have a better way to test timeout than actually
        # waiting.
        def wait():
            time.sleep(TIMEOUT * 3 // 2)
        self.execTest("f()", {'f': wait}, should_error=True)

    ############
    # Test run #
    ############

    def testRun_basicLog(self):
        test_case = MockTestCase(
            lines=[
                '$ x + 2',
            ],
            outputs=[
                '4',
            ],
        )
        error, log = self.console.run(test_case, frame={'x': 2})
        self.assertFalse(error)
        self.assertEqual([
            '>>> x + 2', '\n',
            '4', '\n',
        ], log)

    def testRun_basicLogNoFrame(self):
        test_case = MockTestCase(
            lines=[
                '$ 2 + 2',
            ],
            outputs=[
                '4',
            ],
        )
        error, log = self.console.run(test_case, frame={})
        self.assertFalse(error)
        self.assertEqual([
            '>>> 2 + 2', '\n',
            '4', '\n',
        ], log)

    def testRun_indentNoNewline(self):
        test_case = MockTestCase(
            lines=[
                'def square(x):',
                '    return x * x',
                '$ square(4)',
            ],
            outputs=[
                '16',
            ],
        )
        error, log = self.console.run(test_case, frame={})
        self.assertFalse(error)
        self.assertEqual([
            '>>> def square(x):', '\n',
            '...     return x * x', '\n',
            '>>> square(4)', '\n',
            '16', '\n',
        ], log)

    def testRun_indentWithNewline(self):
        test_case = MockTestCase(
            lines=[
                'def square(x):',
                '    return x * x',
                '',
                '$ square(4)',
            ],
            outputs=[
                '16',
            ],
        )
        error, log = self.console.run(test_case, frame={})
        self.assertFalse(error)
        self.assertEqual([
            '>>> def square(x):', '\n',
            '...     return x * x', '\n',
            '>>> square(4)', '\n',
            '16', '\n',
        ], log)

    def testRun_forLoop(self):
        test_case = MockTestCase(
            lines=[
                'for i in range(3):',
                '    print(i)',
                '$ 3 + 4',
            ],
            outputs=[
                '7',
            ],
        )
        error, log = self.console.run(test_case, frame={})
        self.assertFalse(error)
        self.assertEqual([
            '>>> for i in range(3):', '\n',
            '...     print(i)', '\n',
            '0', '\n',
            '1', '\n',
            '2', '\n',
            '>>> 3 + 4', '\n',
            '7', '\n',
        ], log)

    def testRun_failedPrompt(self):
        test_case = MockTestCase(
            lines=[
                '$ 3 + 4',
            ],
            outputs=[
                '2',
            ],
        )
        error, log = self.console.run(test_case, frame={})
        self.assertTrue(error)
        self.assertEqual([
            '>>> 3 + 4', '\n',
            '7', '\n',
            '# Error: expected 2 got 7', '\n',
        ], log)

    def testRun_failedNonPrompt(self):
        test_case = MockTestCase(
            lines=[
                '1 / 0',
                '$ 3 + 4',
            ],
            outputs=[
                '7',
            ],
        )
        error, log = self.console.run(test_case, frame={})
        self.assertTrue(error)
        self.assertEqual([
            '>>> 1 / 0', '\n',
            'Traceback (most recent call last):', '\n',
            'ZeroDivisionError: division by zero\n', '\n',
        ], log)

    def testRun_failedPromptWithException(self):
        test_case = MockTestCase(
            lines=[
                '$ 1 / 0',
            ],
            outputs=[
                '7',
            ],
        )
        error, log = self.console.run(test_case, frame={})
        self.assertTrue(error)
        self.assertEqual([
            '>>> 1 / 0', '\n',
            'Traceback (most recent call last):', '\n',
            "ZeroDivisionError: division by zero\n", '\n',
            '# Error: expected 7 got ZeroDivisionError', '\n',
        ], log)

class RunTest(unittest.TestCase):
    def setUp(self):
        self.logger = OutputLogger()
        self.console = AutograderConsole(self.logger)

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
        self.outputs = outputs or []
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



