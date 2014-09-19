from utils import timer
import exceptions
import time
import unittest

class TimedTest(unittest.TestCase):
    def testNoTimeout_noArgs(self):
        test_fn = lambda: 42
        result = timer.timed(1, test_fn)
        self.assertEqual(42, result)

    def testNoTimeout_withArgs(self):
        result = timer.timed(1, eval, args=('4 + 2',))
        self.assertEqual(6, result)

    def testNoTimeout_withKargs(self):
        square = lambda x: x * x
        result = timer.timed(1, square, kargs={'x': 3})
        self.assertEqual(9, result)

    def testNoTimeout_withException(self):
        catastrophic = lambda: 1 / 0
        self.assertRaises(ZeroDivisionError, timer.timed, 1, catastrophic)

    def testTimeout(self):
        def waits():
            time.sleep(1)
        self.assertRaises(exceptions.Timeout, timer.timed, 0, waits)
