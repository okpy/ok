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

import argparse
import importlib.machinery
import os
import sys
from urllib import request, error
import json


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


def load_test_file(tests):
    """Return (test_file, assignment) of the test file specified by tests.

    test_file:   full path to the test file
    assignment:  the value of the assignment attribute defined in test_file
    """
    if tests and os.path.exists(tests) and not os.path.isdir(tests):
        assignment = get_assignment(tests)
        if assignment:
            return tests, assignment
    if tests and os.path.isdir(tests):
        return find_test_file(tests, None)

    if tests and os.path.sep in tests:
        if os.path.exists(tests):
            raise Exception('File "{}" is not in ok.py format'.format(tests))
        else:
            raise Exception('File "{}" does not exist'.format(tests))
    else:
        return find_test_file(os.curdir, tests)


def find_test_file(directory, test_file_hint=None):
    """Return (test_file, assignment) of the ok test file in directory.

    The test_file_hint parameter is supplied by the user to disambiguate among
    candidates. In this way, a student can keep multiple assignments in the
    same directory.
    """
    files = os.listdir(directory)
    make_path = lambda f: os.path.normpath(os.path.join(directory, f))
    test_paths = [make_path(f) for f in files if f.endswith('_tests.py')]
    test_contents = [(p, get_assignment(p)) for p in test_paths]
    assignments = {p: a for (p, a) in test_contents if a}

    ex = Exception
    if not assignments:
        abs_dir = os.path.abspath(directory)
        raise ex('No test files found in directory "{}".\n'.format(abs_dir) +
                 'Put ok.py with your assignment or use -t to specify tests.')
    elif len(assignments) == 1 and not test_file_hint:
        return next(iter(assignments.items()))
    elif not test_file_hint:
        raise ex('Multiple test files found: {}\n'.format(list(assignments)) +
                 'Select one using -t followed by any substring contained '
                 'only in the test file you wish to select.')
    else:
        matches = [a for a in assignments if test_file_hint in a]
        if len(matches) == 1:
            match = matches[0]
            return match, assignments[match]
        elif len(matches) == 0:
            raise ex('Test file matching "{}" was not found in: {}'.format(
                test_file_hint, list(assignments)))
        elif len(matches) >= 1:
            raise ex('Multiple test files matching "{}" found: {}'.format(
                test_file_hint, matches))


def get_assignment(path):
    """Attempt to load the source file at path and return the value of its
    assignment attribute. Returns None on failure.
    """
    try:
        loader = importlib.machinery.SourceFileLoader(path, path)
        test_module = loader.load_module()
        return test_module.assignment
    except Exception:
        return None


def get_src_paths(test_file, src_files):
    """Return paths to src_files by prepending test_file enclosing dir."""
    directory, _ = os.path.split(test_file)
    return [os.path.join(directory, f) for f in src_files]


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
