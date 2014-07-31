#!/usr/bin/python3

"""The ok.py script runs tests, checks for updates, and saves your work.

Common uses:
  python3 ok.py          Run unlocked tests (and save your work).
  python3 ok.py -u       Unlock new tests interactively.
  python3 ok.py -h       Display full help documentation.

This script will search the current directory for assignments. Make sure that
ok.py appears in the same directory as the assignment you wish to test.
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
server, processed by on_start and on_response methods. If other interactions
are required outside of this lifecycle, the send_to_server function can be used
to send and receive information from the server outside of the default times.
Such communications should be limited to the body of an on_interact method.
"""

import argparse
import itertools
import os
import sys
from urllib import request, error
import json


class Protocol(object):
    """TODO(denero) Describe protocols, once we actually know what they do."""
    name = None

    def __init__(self, cmd_line_args, src_files):
        self.args = cmd_line_args  # A dictionary of parsed arguments
        self.src_files = src_files # A list of paths

    def on_start(self):
        """Called when ok.py starts. Returns an object to be sent to server."""

    def on_response(self, response):
        """Called when ok-server responds with the server response."""

    def on_interact(self):
        """Called to execute an interactive or output-intensive session."""


class FileContents(Protocol):
    """The contents of changed source files are sent to the server."""
    name = 'file_contents'

    def on_start(self):
        """Find all source files and return their complete contents."""
        contents = {}
        for path in self.src_files:
            key = os.path.normpath(path)
            with open(path, 'r', encoding='utf-8') as lines:
                value = lines.read()
            contents[key] = value
        return contents


class RunTests(Protocol):
    """Runs tests, formats results, and sends results to the server."""
    name = 'run_tests'

    def on_interact(self):
        """Run unlocked tests and print results."""
        # TODO(denero) Import all the existing autograder functionality here.


def send_to_server(messages, assignment, server, endpoint='submission/new'):
    """Send messages to server, along with user authentication."""
    data = {
        'access_token': 'TODO', # TODO(denero) Add cached auth token.
        'assignment': assignment,
        'messages': messages,
    }
    try:
        # TODO(denero) Change to https.
        address = 'http://' + server + '/api/v1/' + endpoint
        serialized = json.dumps(data).encode(encoding='utf-8')
        # TODO(denero) Wrap in timeout.
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
    parser.add_argument('-a', '--assignment', metavar='A', type=str,
                        help="assignment name to check (partial names are ok)")
    parser.add_argument('-q', '--question', type=int,
                        help="focus on a specific question")
    parser.add_argument('-r', '--root', type=str, default=None,
                        help="path to root directory of assignment")
    parser.add_argument('-s', '--server', type=str, default='localhost:8080',
                        help="server address")
    parser.add_argument('-u', '--unlock', action='store_true',
                        help="unlock tests interactively")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="print more output")
    return parser.parse_args()


def is_src_file(filename):
    """Return whether filename is an assignment source file."""
    return filename.endswith('.py') and \
        filename != 'ok.py' and \
        not filename.endswith('_tests.py')


def get_assignment(path):
    """Return the assignment name corresponding to a source file.

    We read the file directly rather than loading it to be robust to syntax
    errors that may appear in the files being examined.
    """
    with open(path, 'r') as lines:
        for line in lines:
            if 'ASSIGNMENT' in line:
                parts = line.split('ASSIGNMENT', 2)
                if len(parts) == 2:
                    after = parts[1]
                    return after.strip(' =#\t\n)\'"')
    return None


def group_by_assignment(paths):
    """Build map from assignments to lists of source files."""
    assignments = dict()
    for path in paths:
        assignment = get_assignment(path)
        if assignment:
            assignments.setdefault(assignment, []).append(path)
    return assignments


def find_assignment(assignment_hint, root, max_files=1000):
    """Return (assignment_name, src_files_list) pair. Exits on failure.

    The assignment_hint parameter is supplied by the user to disambiguate among
    candidates. In this way, a student can keep multiple assignments in the
    same directory.
    """
    files = itertools.islice(os.walk(root), 0, max_files)
    join = os.path.join
    paths = [join(d, f) for (d, _, fs) in files for f in fs if is_src_file(f)]
    assignments = group_by_assignment(paths)

    ex = Exception
    if not assignments:
        raise ex('No assignment found in directory "{}".\n'.format(root) +
                 'Put ok.py with your assignment or use -r to specify a root.')
    elif len(assignments) == 1 and not assignment_hint:
        return next(iter(assignments.items()))
    elif not assignment_hint:
        raise ex('Multiple assignments found: {}\n'.format(list(assignments)) +
                 'Select one using -a followed by any unique substring of the '
                 'assignment you wish to select.')
    else:
        matches = [a for a in assignments if assignment_hint in a]
        if len(matches) == 1:
            match = matches[0]
            return match, assignments[match]
        elif len(matches) == 0:
            raise ex('Assignment matching "{}" was not found in: {}'.format(
                assignment_hint, list(assignments)))
        elif len(matches) >= 1:
            raise ex('Multiple assignments matching "{}" found: {}'.format(
                assignment_hint, matches))


def ok_main(args):
    """Run all relevant aspects of ok.py."""
    ok_root = os.path.abspath(os.path.split(sys.argv[0])[0])
    root = args.root if args.root else ok_root
    try:
        assignment, src_files = find_assignment(args.assignment, root)
    except Exception as ex:
        print(ex)
        sys.exit(1)

    start_protocols = [p(args, src_files) for p in [FileContents]]
    interact_protocols = [p(args, src_files) for p in [RunTests]]

    messages = dict()
    for protocol in start_protocols:
        messages[protocol.name] = protocol.on_start()

    # TODO(denero) Send and receive in a separate thread.
    send_to_server(messages, assignment, args.server)

    for protocol in interact_protocols:
        protocol.on_interact()

    # Handle server response

if __name__ == '__main__':
    ok_main(parse_input())
