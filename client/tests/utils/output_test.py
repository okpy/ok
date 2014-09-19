from unittest import mock
from utils import output
import sys
import unittest

class OutputLoggerTest(unittest.TestCase):
    """Tests the OutputLogger."""

    def setUp(self):
        self.mock_output = mock.MagicMock(spec=output.OutputLogger)
        # The OutputLogger will think stdout was the MockOutputStream.
        sys.stdout = self.mock_output
        self.logger = sys.stdout = output.OutputLogger()

    def tearDown(self):
        sys.stdout = sys.__stdout__

    def testLoggerOn(self):
        self.logger.on()
        print("logger on 1")
        print("logger on 2")
        self.assertTrue(self.logger.is_on())
        self.assertTrue(self.mock_output.write.called)

    def testLoggerOff(self):
        self.logger.off()
        print("logger off 1")
        print("logger off 2")
        self.assertFalse(self.logger.is_on())
        self.assertFalse(self.mock_output.write.called)

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

