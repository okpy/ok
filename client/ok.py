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
server. If other interactions are required outside of this lifecycle, the
functions send_to_server and receive_from_server can be used to send and
receive information from the server outside of the default times.
"""
import argparse


class Protocol(object):
    """TODO(denero) Describe protocols, once we actually know what they do."""
    name = None

    def __init__(self, cmd_line_args):
        self.args = cmd_line_args # A dictionary of parsed arguments.

    def on_start(self, buf):
        """Always called when ok.py starts. """
        pass

    def on_interact(self, buf):
        """
        TODO(denero) I don't understand what on_interact is supposed to do.

        This method is called if the student chooses the mode that specifically
        selects this protocol. This might also be called in another protocol's
        on_interact method as well.
        """
        pass


class FileContents(Protocol):
    """The contents of changed source files are sent to the server."""
    name = 'file_contents'


class RunTests(Protocol):
    """Runs tests, formats results, and sends results to the server."""
    file = 'test_results'


def send_to_server(buf):
    """
    This depends on the server-side API. But this method will construct
    an HTTPS request and send it to the server according to the API.
    """
    # Insert code for sending to the server here...

    buf.clear()
    buf[STUDENT_KEY] = STUDENT_LOGIN
    buf[MSG_TYPE] = MSG_INTERACT


def receive_from_server():
    """
    This also depends on the server side API, but it might need to take
    in a list of connections- to be decided.

    Returns a response from the server.
    """
    pass

# Configuration variables and runtime methods

STUDENT_LOGIN = ""
STUDENT_KEY = 'student'
MSG_TYPE = 'msg_type'
MSG_START = 'start'
MSG_INTERACT = 'interact'

# TODO(denero) Pass around a buffer that checks for message duplication, rather
#              than using a global variable with shared access.
INPUT_BUFFER = {STUDENT_KEY : STUDENT_LOGIN, MSG_TYPE : MSG_START}

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
