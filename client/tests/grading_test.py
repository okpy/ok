import sys
import time
import unittest
from utils import OutputLogger, TIMEOUT
from grading import AutograderConsole

class AutograderConsoleTest(unittest.TestCase):
    def setUp(self):
        # TODO(albert): consider using an actual OutputLogger to
        # better test run.
        self.logger = sys.stdout = OutputLogger()
        self.console = AutograderConsole(self.logger)

    def tearDown(self):
        sys.stdout = sys.__stdout__

    #############
    # Test exec #
    #############

    def testExec_expectedWithNoErrors(self):
        expr = "x + 4"
        errored = self.console.exec(expr, {'x': 3}, expected='7')
        self.assertFalse(errored)

    def testExec_expectedWithNoEqualsError(self):
        expr = "2 + 4"  # Equals 6, not 7.
        errored = self.console.exec(expr, {}, expected='7')
        self.assertTrue(errored)

    def testExec_expectedExceptionWithNoError(self):
        expr = "1 / 0"  # Causes ZeroDivisionError
        errored = self.console.exec(expr, {},
                expected='ZeroDivisionError')
        self.assertFalse(errored)

    def testExec_expectedExceptionWithNotEqualsError(self):
        expr = "1 + 2"
        errored = self.console.exec(expr, {},
                expected='ZeroDivisionError')
        self.assertTrue(errored)

    def testExec_expectedExceptionWithWrongException(self):
        expr = "1 / 0"
        errored = self.console.exec(expr, {},
                expected='TypeError')
        self.assertTrue(errored)

    def testExec_runtimeError(self):
        expr = "f()"
        max_recursion = lambda: max_recursion()
        errored = self.console.exec(expr, {'f': max_recursion})
        self.assertTrue(errored)

    def testExec_timeoutError(self):
        # TODO(albert): have a better way to test timeout than actually
        # waiting.
        expr = "f()"
        def wait():
            time.sleep(TIMEOUT * 3 // 2)
        errored = self.console.exec(expr, {'f': wait})
        self.assertTrue(errored)

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

#########
# Mocks #
#########

class MockTestCase:
    def __init__(self, lines=None, outputs=None, status=None,
            q_type=None, teardown=None):
        self.lines = lines or []
        self.outputs = outputs or []
        self.status = status or {}
        self.type = q_type or ''
        self.teardown = teardown or []

