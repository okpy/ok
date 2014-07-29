#!/usr/bin/python3

"""The ok.py script runs tests, checks for updates, and saves your work.

Common uses:
  python3 ok.py        Run unlocked tests, check for updates, and save work.
  python3 ok.py -u     Unlock new tests interactively.
  python3 ok.py -h     Display full help documentation.

This script will search the current directory for assignments. Make sure that
ok.py appears in the same directory as the assignment you wish to test.
"""

# TODO(denero) Add mechanism for removing DEVELOPER INSTRUCTIONS.
"""DEVELOPER INSTRUCTIONS

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


class Protocol(object):
    """TODO(denero) Describe protocols, once we actually know what they do."""
    name = None

    def __init__(self, cmd_line_args):
        self.args = cmd_line_args # A dictionary of parsed arguments.

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


class RunTests(Protocol):
    """Runs tests, formats results, and sends results to the server."""
    name = 'run_tests'

    def on_interact(self):
        """Run unlocked tests and print results."""


def send_to_server(messages):
    """Send messages to server, along with user authentication."""
    # TODO(denero) Send an {access_token, assignment, messages} post.


# TODO(denero) Pass around a buffer that checks for message duplication, rather
#              than using a global variable with shared access.
INPUT_BUFFER = {}

PROTOCOLS = list()

def parse_input():
    """Parses command line input."""
    parser = argparse.ArgumentParser(description="Autograder parser")
    parser.add_argument('-m', '--mode', type=str, default=None,
                        help="Mode the autograder should run in.")
    return parser.parse_args()

def ok_main(cmd_line_args):
    """Run all relevant aspects of ok.py."""
    name_to_protocol = dict()

    for protocol in PROTOCOLS:
        proto_inst = protocol(cmd_line_args)
        name_to_protocol[protocol.name] = proto_inst
        proto_inst.on_start(INPUT_BUFFER)

    send_to_server(INPUT_BUFFER)

    if cmd_line_args.mode != None:
        name_to_protocol[cmd_line_args.mode].on_interact(INPUT_BUFFER)

    send_to_server(INPUT_BUFFER)

if __name__ == '__main__':
    ok_main(parse_input())
