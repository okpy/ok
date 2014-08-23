#!/usr/bin/python3

"""The ok.py script runs tests, checks for updates, and saves your work.

Common uses:
  python3 ok.py          Run unlocked tests (and save your work).
  python3 ok.py -u       Unlock new tests interactively.
  python3 ok.py -h       Display full help documentation.

This script will search the current directory for test files. Make sure that
ok.py appears in the same directory as the assignment you wish to test.
Otherwise, use -t to specify a test file manually.
"""

# TODO(denero) Add mechanism for removing DEVELOPER INSTRUCTIONS.
DEVELOPER_INSTRUCTIONS = """

This multi-line string contains instructions for developers. It is removed
when the client is distributed to students.

This file is responsible for coordinating all communication with the ok-server.
Students should never need to modify this file.

Local and remote interactions are encapsulated as protocols.
Contributors should do the following to add a protocol to this autograder:

    1- Extend the Protocol class and implement on_start and on_interact.
    2- Add the classname of your protocol to the "protocols" list.
    3- If your protocol needs command line arguments, change parse_input.

A standard protocol lifecycle has only one round-trip communication with the
server, processed by the on_start method. If other interactions are required
outside of this lifecycle, the send_to_server function can be used to send and
receive information from the server outside of the default times. Such
communications should be limited to the body of an on_interact method.
"""

from models import core
from urllib import request, error
import argparse
import importlib.machinery
import json
import os
import sys


class Protocol(object):
    """A Protocol encapsulates a single aspect of ok.py functionality."""
    name = None # Override in sub-class.

    def __init__(self, cmd_line_args, src_files):
        self.args = cmd_line_args  # A namespace of parsed arguments
        self.src_files = src_files # A list of paths to student source files

    def on_start(self):
        """Called when ok.py starts. Returns an object to be sent to server."""

    def on_interact(self):
        """Called to execute an interactive or output-intensive session."""


class FileContents(Protocol):
    """The contents of changed source files are sent to the server."""
    name = 'file_contents'

    def on_start(self):
        """Find all source files and return their complete contents."""
        contents = {}
        for path in self.src_files:
            key = os.path.normpath(os.path.split(path)[1])
            with open(path, 'r', encoding='utf-8') as lines:
                value = lines.read()
            contents[key] = value
        return contents


class RunTests(Protocol):
    """Runs tests, formats results, and sends results to the server."""
    name = 'run_tests'

    def on_interact(self):
        """Run unlocked tests and print results."""
        # TODO(denero) Run all tests.


def send_to_server(messages, assignment, server, endpoint='submission/new'):
    """Send messages to server, along with user authentication."""
    data = {
        'assignment': assignment,
        'messages': messages,
    }
    try:
        # TODO(denero) Change to https.
        address = 'http://' + server + '/api/v1/' + endpoint
        serialized = json.dumps(data).encode(encoding='utf-8')
        # TODO(denero) Wrap in timeout (maybe use PR #51 timed execution).
        # TODO(denero) Send access token with the request
        req = request.Request(address)
        req.add_header("Content-Type", "application/json")
        response = request.urlopen(req, serialized)
        return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as ex:
        print("Error while sending to server: {}".format(ex))
        response = ex.file.read().decode('utf-8')
        message = json.loads(response)['message']
        indented = '\n'.join('\t' + line for line in message.split('\n'))
        print(indented)
        return {}


class OkException(BaseException):
    pass

######################
# Assignment loading #
######################

TEST_DIR = 'tests'
INFO_FILE = 'info.py'

def load_assignment(assignment):
    """Loads information and tests for the given assignment.

    PARAMETERS:
    assignment -- str; a filepath to an assignment. An assignment is
                  defined as a directory that contains a subdirectory
                  called "tests". This subdirectory must contain a file
                  called "info". The assignment filepath should be
                  specified relative to ok.py.

    RETURNS:
    (info, tests), where
    info  -- dict; information related to the assignment
    tests -- list of Tests; all the tests related to the assignment.
    """
    if not _isdir(assignment):
        raise OkException('Assignment "{}" must be a directory'.format(
            assignment))
    test_dir = os.path.join(assignment, TEST_DIR)
    if not _isdir(test_dir):
        raise OkException('Assignment "{}" must have a {} directory'.format(
            assignment, TEST_DIR))
    info_file = os.path.join(test_dir, INFO_FILE)
    if not _isfile(info_file):
        raise OkException('Directory {} must have a file called {}'.format(
            test_dir, INFO_FILE))
    info = _get_info(info_file)
    tests = _get_tests(test_dir, info)
    return info, tests


def _get_info(filepath):
    """Loads information from an INFO file, given by the filepath.

    PARAMETERS:
    filepath -- str; filepath to an INFO file.

    RETURNS:
    dict; information contained in the INFO file.
    """
    # TODO(albert): add error handling in case no attribute test is
    # found.
    return _import_module(filepath).info


def _get_tests(directory, info):
    """Loads all tests in a tests directory.

    PARAMETER:
    directory -- str; filepath to a directory that contains tests.
    info      -- dict; top-level information about the assignment,
                 extracted from info.py

    RETURNS:
    list of Tests; each file in the tests/ directory is turned into a
    Test object.
    """
    test_files = _listdir(directory)
    tests = []
    for file in test_files:
        if file == INFO_FILE:
            continue
        path = os.path.normpath(os.path.join(directory, file))
        if _isfile(path):
            # TODO(albert): add error handling in case no attribute
            # test is found.
            test = _import_module(path).test
            tests.append(core.Test.serialize(test, info))
        elif _isdir(file):
            # TODO(albert): recursively load tests?
            pass
    return tests


def get_src_paths(test_file, src_files):
    """Return paths to src_files by prepending test_file enclosing dir."""
    directory, _ = os.path.split(test_file)
    return [os.path.join(directory, f) for f in src_files]

###############################################
# These functions are for overriding in tests #
###############################################

def _isdir(path):
    return os.path.isdir(path)

def _isfile(path):
    return os.path.isfile(path)

def _listdir(path):
    return os.listdir(path)

def _import_module(path):
    """Attempt to load the source file at path. Returns None on failure."""
    try:
        loader = importlib.machinery.SourceFileLoader(path, path)
        test_module = loader.load_module()
        return test_module
    except Exception:
        # TODO(albert): should probably fail fast.
        return None

##########################
# Command-line Interface #
##########################

def parse_input():
    """Parses command line input."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-q', '--question', type=str,
                        help="focus on a specific question")
    parser.add_argument('-s', '--server', type=str, default='localhost:8080',
                        help="server address")
    parser.add_argument('-t', '--tests', metavar='A', type=str,
                        help="partial name or path to test file or directory")
    parser.add_argument('-u', '--unlock', action='store_true',
                        help="unlock tests interactively")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="print more output")
    return parser.parse_args()


def ok_main(args):
    """Run all relevant aspects of ok.py."""
    try:
        test_file, assignment = load_test_file(args.tests)
        src_files = get_src_paths(test_file, assignment['src_files'])
    except Exception as ex:
        print(ex)
        sys.exit(1)

    start_protocols = [p(args, src_files) for p in [FileContents]]
    interact_protocols = [p(args, src_files) for p in [RunTests]]

    messages = dict()
    for protocol in start_protocols:
        messages[protocol.name] = protocol.on_start()

    # TODO(denero) Send in a separate thread.
    send_to_server(messages, assignment, args.server)

    for protocol in interact_protocols:
        protocol.on_interact()

    # TODO(denero) Print server responses.

if __name__ == '__main__':
    ok_main(parse_input())
