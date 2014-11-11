from client.protocols import file_contents
from unittest import mock
import os
import unittest

DEMO = 'client/demo_assignments'
INVALID = os.path.join(DEMO, 'invalid')
VALID = os.path.join(DEMO, 'valid')
TMP = os.path.join(DEMO, 'tmp')

class TestFileContentsProtocol(unittest.TestCase):
    SRC_FILE = os.path.join(VALID, 'hw1', 'hw1.py')

    def setUp(self):
        cmd_line_args = mock.Mock()
        self.assignment = mock.MagicMock()
        self.assignment.__getitem__.return_value =  [self.SRC_FILE]
        self.logger = mock.Mock()
        self.proto = file_contents.FileContents(cmd_line_args, self.assignment, self.logger)

    def test_on_start(self):
        contents = self.proto.on_start()
        self.assertIn('hw1.py', contents)
        self.assertIn('def square(x):', contents['hw1.py'])
