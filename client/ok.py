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
from utils import OutputLogger
from urllib import request, error
import argparse
import importlib.machinery
import json
import os
import sys

from auth import authenticate

class Protocol(object):
    """A Protocol encapsulates a single aspect of ok.py functionality."""
    name = None # Override in sub-class.

    def __init__(self, cmd_line_args, info, tests, logger):
        """Constructor.

        PARAMETERS:
        cmd_line_args -- Namespace; parsed command line arguments.
                         command line, as parsed by argparse.
        info          -- dict; general information about the assignment.
        tests         -- list of Tests
        logger        -- OutputLogger; used to control output
                         destination, as well as capturing output from
                         an autograder session.
        """
        self.args = cmd_line_args
        self.info = info
        self.tests = tests
        self.logger = logger

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
        for path in self.info['src_files']:
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
        'assignment': assignment['name'],
        'messages': messages,
    }
    try:
        address = 'http://' + server + '/api/v1/' + endpoint
        serialized = json.dumps(data).encode(encoding='utf-8')
        # TODO(denero) Wrap in timeout (maybe use PR #51 timed execution).
        # TODO(denero) Send access token with the request
        access_token = authenticate()
        address += "?access_token=%s" % access_token
        req = request.Request(address)
        req.add_header("Content-Type", "application/json")
        response = request.urlopen(req, serialized)
        return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as ex:
        print("Error while sending to server: {}".format(ex))
        response = ex.read().decode('utf-8')
        message = json.loads(response)['message']
        indented = '\n'.join('\t' + line for line in message.split('\n'))
        print(indented)
        return {}


class OkException(BaseException):
    """Exception class for ok.py"""
    pass

######################
# Assignment loading #
######################

INFO_FILE = 'info.py'

def load_tests(test_dir):
    """Loads information and tests for the current assignment.

    PARAMETERS:
    test_dir -- str; a filepath to the test directory, 'tests' by default.
                  An assignment is defined as a directory that contains
                  a subdirectory called "tests". This subdirectory must
                  contain a file called "info.py". The filepath
                  should be specified relative to ok.py.

    RETURNS:
    (info, tests), where
    info  -- dict; information related to the assignment
    tests -- list of Tests; all the tests related to the assignment.
    """
    if not os.path.isdir(test_dir):
        raise OkException('Assignment must have a {} directory'.format(test_dir))
    info_file = os.path.join(test_dir, INFO_FILE)
    if not os.path.isfile(info_file):
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
    # TODO(albert): add error handling in case no attribute info is
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
    test_files = os.listdir(directory)
    tests = []
    for file in test_files:
        if file == INFO_FILE or not file.endswith('.py'):
            continue
        path = os.path.normpath(os.path.join(directory, file))
        if os.path.isfile(path):
            # TODO(albert): add error handling in case no attribute
            # test is found.
            test = _import_module(path).test
            tests.append(core.Test.serialize(test, info))
    return tests


def _import_module(path):
    """Attempt to load the source file at path. Returns None on failure."""
    try:
        loader = importlib.machinery.SourceFileLoader(path, path)
        test_module = loader.load_module()
        return test_module
    except Exception:
        # TODO(albert): should probably fail fast, but with helpful
        # error messages.
        return None


def get_src_paths(assignment):
    """Return paths to src_files by prepending test_file enclosing dir."""
    return assignment['src_files']

##########################
# Command-line Interface #
##########################

def parse_input():
    """Parses command line input."""
    # TODO(albert): rethink these command line arguments. One edit is
    # to change the --tests flag to --assignment, a relative path to
    # the assignment directory.
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-q', '--question', type=str,
                        help="focus on a specific question")
    parser.add_argument('-s', '--server', type=str, default='localhost:8080',
                        help="server address")
    parser.add_argument('-t', '--tests', metavar='A', default='tests', type=str,
                        help="partial name or path to test file or directory")
    parser.add_argument('-u', '--unlock', action='store_true',
                        help="unlock tests interactively")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="print more output")
    return parser.parse_args()


def ok_main(args):
    """Run all relevant aspects of ok.py."""
    # TODO(albert): rewrite this function to use load_assignment to
    # read test files. Also modify the Protocol constructor's
    # parameters.
    try:
        assignment, tests = load_tests(args.tests)
    except Exception as ex:
        raise ex
        print(ex)
        sys.exit(1)

    logger = OutputLogger()
    #TODO: albert do stuff

    start_protocols = [p(args, assignment, tests, logger) for p in [FileContents]]
    interact_protocols = [p(args, assignment, tests, logger) for p in [RunTests]]

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
