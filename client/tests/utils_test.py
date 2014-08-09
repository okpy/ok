import unittest
import sys
import time
import utils
from utils import OutputLogger, timed, TimeoutError, TIMEOUT

class OutputLoggerTest(unittest.TestCase):
    """Tests the OutputLogger."""

    def setUp(self):
        self.mock_output = MockOutputStream()
        # The OutputLogger will think stdout was the MockOutputStream.
        sys.stdout = self.mock_output
        self.logger = sys.stdout = OutputLogger()

    def tearDown(self):
        sys.stdout = sys.__stdout__

    def testLoggerOn(self):
        self.logger.on()
        print("logger on 1")
        print("logger on 2")
        self.assertTrue(self.logger.isOn())
        self.assertLess(0, self.mock_output.called('write'))

    def testLoggerOff(self):
        self.logger.off()
        print("logger off 1")
        print("logger off 2")
        self.assertFalse(self.logger.isOn())
        self.assertEqual(0, self.mock_output.called('write'))

    def testRegisterLog_loggerOn(self):
        log = []
        self.logger.register_log(log)
        self.logger.on()

        print("message 1")
        print("message 2")

        self.assertEqual(["message 1", "\n", "message 2", "\n"], log)

    def testRegisterLog_loggerOff(self):
        log = []
        self.logger.register_log(log)
        self.logger.off()

        print("message 1")
        print("message 2")

        self.assertEqual(["message 1", "\n", "message 2", "\n"], log)

    def testRegisterLog_logIsNone(self):
        self.logger.register_log(None)
        self.logger.on()

        # The following should not cause any errors.
        print("message 1")
        print("message 2")

class TimedTest(unittest.TestCase):
    # TODO(albert): have a better way to test timeout rather than
    # actually waiting for a timeout.

    def testNoTimeout_noArgs(self):
        test_fn = lambda: 42
        result = timed(test_fn)
        self.assertEqual(42, result)

    def testNoTimeout_withArgs(self):
        result = timed(eval, args=('4 + 2',))
        self.assertEqual(6, result)

    def testNoTimeout_withKargs(self):
        square = lambda x: x * x
        result = timed(square, kargs={'x': 3})
        self.assertEqual(9, result)

    def testNoTimeout_withException(self):
        catastrophic = lambda: 1 / 0
        self.assertRaises(ZeroDivisionError, timed, catastrophic)

    def testTimeout_defaultTimeout(self):
        def waits():
            time.sleep(2 * utils.TIMEOUT)
        self.assertRaises(TimeoutError, timed, waits)

    def testTimeout_timeoutAsArgument(self):
        def waits():
            time.sleep(TIMEOUT // 2)
        self.assertRaises(TimeoutError, timed,
                fn=waits, timeout=TIMEOUT // 4)

#########
# Mocks #
#########

class MockOutputStream(object):
    """A mock output stream for testing the OutputLogger class.

    The mock simply keeps track of the number of times each attribute
    is retrieved. It otherwise behaves exactly like sys.__stdout__.
    """
    def __init__(self):
        self.counter = {}

    def __getattr__(self, attr):
        self.counter[attr] = self.counter.get(attr, 0) + 1
        return getattr(sys.__stdout__, attr)

    def called(self, attr):
        """Returns the number of times attr was retrieved."""
        return self.counter.get(attr, 0)

