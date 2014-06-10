""" The client side autograder functionality.

This file is responsible for all communication with the server and will contain
all protocols that are used in this project. Students should never need to
modify this file and staff should change the "protocols" list in the
configuration variables to include the protocols that they wish to use for the
project.


Contributors should do the following to add a protocol to this autograder:

    1- Extend the Protocol class and implement on_start and on_interact.
    2- Add the classname of your protocol to the "protocols" list.
    3- If your protocol needs command line arguments, change parse_input.

The only useful methods in the framework code are send_to_server and
receive_from_server, which should be invoked if you wish to send information to
the server or receive information from the server outside of the default times.
"""

import argparse

# Template protocol. All protocols must subclass this.

class Protocol(object):
    """
    The template class that all protocols must follow.
    """
    name = None

    def __init__(self, cmd_line_args):
        """
        Initializes an instance of the Protocol class.
        """
        self.args = cmd_line_args

    def on_start(self, buf):
        """
        This method is called only once, which is when the autograder first
        starts. It is called every time that the autograder starts, regardless
        of what mode the student wants to run the autograder in.
        """
        pass

    def on_interact(self, buf):
        """
        This method is called if the student chooses the mode that specifically
        selects this protocol. This might also be called in another protocol's
        on_interact method as well.
        """
        pass

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

INPUT_BUFFER = {STUDENT_KEY : STUDENT_LOGIN, MSG_TYPE : MSG_START}

PROTOCOLS = list()

def parse_input():
    """
    Parses command line input from the student.
    """
    parser = argparse.ArgumentParser(description="Autograder parser")
    parser.add_argument('-m', '--mode', type=str, default=None,
                        help="Mode the autograder should run in.")

    args = parser.parse_args()

    return args

def ok_main(cmd_line_args):
    """
    The main method for this module that is run when it is invoked.
    """
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
