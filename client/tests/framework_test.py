from models import core
from unittest import mock
import ok
import os
import sys
import unittest

class TestProtocol(ok.Protocol):
    def __init__(self, args, src_files):
        ok.Protocol.__init__(args, src_files)
        self.called_start = 0
        self.called_interact = 0

    def on_start(self):
        self.called_start += 1

    def on_interact(self):
        self.called_interact += 1


class TestOK(unittest.TestCase):
    def test_parse_input(self):
        old_sys_argv = sys.argv[1:]
        sys.argv[1:] = []
        _ = ok.parse_input() # Does not crash and returns a value.
        sys.argv[1:] = old_sys_argv


class MockFileSystem(object):
    def __init__(self, directories, files):
        self._directories = directories
        self._files = files

    def isdir(self, path):
        return path in self._directories

    def isfile(self, path):
        return path in self._files

    def listdir(self, path):
        assert path in self._directories, "listdir called on file"
        return [os.path.basename(f) for f in self._files
                                    if os.path.dirname(f) == path]

    def exists(self, path):
        return path in self._files or self._directories

class TestLoadAssignment(unittest.TestCase):

    VALID_ASSIGN = 'hw1'
    ASSIGN_NO_TESTS = 'hw2'
    ASSIGN_NO_INFO = 'hw3'
    NONEXISTENT_ASSIGN = 'bogus'

    def setUp(self):
        self.filesystem = self.makeMockFilesystem()
        self.sample_test = core.Test()
        self.mock_info = mock.MagicMock()
        self.applyPatches()

    #########
    # Tests #
    #########

    def testNonExistentAssignment(self):
        self.assertRaises(ok.OkException, ok.load_assignment,
                          self.NONEXISTENT_ASSIGN)

    def testMissingTestDirectory(self):
        self.assertRaises(ok.OkException, ok.load_assignment,
                          self.ASSIGN_NO_TESTS)

    def testMissingInfo(self):
        self.assertRaises(ok.OkException, ok.load_assignment,
                          self.ASSIGN_NO_INFO)

    def testLoadValidAssignment_info(self):
        info, _ = ok.load_assignment(self.VALID_ASSIGN)
        self.assertIs(self.mock_info, info)

    def testLoadValidAssignment_tests(self):
        _, tests = ok.load_assignment(self.VALID_ASSIGN)
        self.assertEqual([self.sample_test, self.sample_test], tests)
        self.assertEqual(2, len(core.Test.serialize.mock_calls))

    #############
    # Utilities #
    #############

    def makeMockFilesystem(self):
        """Creates a mock filesystem with valid assignments and invalid
        assignments.
        """
        valid_assign_directories = [
            self.VALID_ASSIGN,
            os.path.join(self.VALID_ASSIGN, ok.TEST_DIR),
        ]
        valid_assign_files = [
            os.path.join(self.VALID_ASSIGN, 'starter.py'),
            os.path.join(self.VALID_ASSIGN, ok.TEST_DIR, ok.INFO_FILE),
            os.path.join(self.VALID_ASSIGN, ok.TEST_DIR, 'q1.py'),
            os.path.join(self.VALID_ASSIGN, ok.TEST_DIR, 'q2.py'),
        ]

        invalid_assign_directories = [
            self.ASSIGN_NO_TESTS,    # Missing tests directory
            self.ASSIGN_NO_INFO,     # Missing info.py
            os.path.join(self.ASSIGN_NO_INFO, ok.TEST_DIR)
        ]
        return MockFileSystem(
                valid_assign_directories + invalid_assign_directories,
                valid_assign_files)

    def applyPatches(self):
        """Applies unittest patches (temporary mocks) to filesystem
        utility methods, as well as the Test.serialize method.
        """
        # Patch ok._isdir to search MockFileSystem
        isdir_patcher = mock.patch('ok._isdir')
        isdir = isdir_patcher.start()
        isdir.side_effect = self.filesystem.isdir
        self.addCleanup(isdir_patcher.stop)

        # Patch ok._isfile to search MockFileSystem
        isfile_patcher = mock.patch('ok._isfile')
        isfile = isfile_patcher.start()
        isfile.side_effect = self.filesystem.isfile
        self.addCleanup(isfile_patcher.stop)

        # Patch ok._listdir to search MockFileSystem
        listdir_patcher = mock.patch('ok._listdir')
        listdir = listdir_patcher.start()
        listdir.side_effect = self.filesystem.listdir
        self.addCleanup(listdir_patcher.stop)

        # Patch ok._import_module to search MockFileSystem
        import_module_patcher = mock.patch('ok._import_module')
        import_module = import_module_patcher.start()
        import_module.side_effect = self._import_module
        self.addCleanup(import_module_patcher.stop)

        # Patch Test.serialize to always return self.sample_test
        serialize_patcher = mock.patch('models.core.Test.serialize',
                                       autospec=core.Test.serialize)
        serialize = serialize_patcher.start()
        serialize.return_value = self.sample_test
        self.addCleanup(serialize_patcher.stop)

    def _import_module(self, path):
        """Returns a mock module based on the path.

        The behavior of this method depends on the specification
        for test file formats -- see the demo_assignments directory
        for examples.

        Currently, there are two types of testing files:

        * info.py: contains a single global variable called "info".
        * test file: for example, q1.py in demo_assignments. Contains
          a single global variable called "test".
        """
        assert self.filesystem.isfile(path), 'Importing non-file: {}' + path
        assert ok.TEST_DIR in path, 'File {} is not a test file'.format(path)
        if path.endswith(ok.INFO_FILE):
            mock_module = mock.Mock(spec=['info'])
            mock_module.info = self.mock_info
        elif ok.TEST_DIR in path:
            mock_module = mock.Mock(spec=['test'])
        return mock_module


class DummyArgs:
    """Placeholder for parsed command-line arguments."""


# TODO(albert): rewrite these tests to use a mock filesystem.
# class TestFileContentsProtocol(unittest.TestCase):
#     def setUp(self):
#         self.hw1 = 'demo_assignments/hw1.py'
#         cmd_line_args = DummyArgs()
#         self.proto = ok.FileContents(cmd_line_args, [self.hw1])
#
#     def test_on_start(self):
#         contents = self.proto.on_start()
#         self.assertEqual(1, len(contents))
#         self.assertIn('hw1.py', contents)
#         self.assertIn('def square(x):', contents['hw1.py'])
