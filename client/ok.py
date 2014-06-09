import argparse

# Template protocol. All protocols must subclass this.

class Protocol(object):
    name = None

    def __init__(self, cmd_line_args):
        self.args = cmd_line_args

    def on_start(self, buf):
        pass

    def on_interact(self, buf):
        pass

def send_to_server(buf):
    """
    This depends on the server-side API. But this method will construct
    an HTTPS request and send it to the server according to the API.
    """
    # Insert code for sending to the server here...

    buf.clear()
    buf[STUDENT_KEY] = student_login
    buf[MSG_TYPE] = MSG_INTERACT

def receive_from_server():
    """
    This also depends on the server side API, but it might need to take
    in a list of connections- to be decided.

    Returns a response from the server.
    """
    pass

# Configuration variables and runtime methods

student_login = ""
STUDENT_KEY = 'student'
MSG_TYPE = 'msg_type'
MSG_START = 'start'
MSG_INTERACT = 'interact'

input_buffer = {STUDENT_KEY : student_login, MSG_TYPE : MSG_START}

protocols = list()

name_to_protocol = dict((proto.name, proto) for proto in protocols)

def parse_input():
    parser = argparse.ArgumentParser(description = "Autograder parser")
    parser.add_argument('-m', '--mode', type=str, default=None,
                        help="Specify the mode you want to run the autograder in.")

    args = parser.parse_args()

    return args

def ok_main(cmd_line_args):
    name_to_protocol = dict()

    for protocol in protocols:
        proto_inst = protocol(cmd_line_args)
        name_to_protocol[protocol.name] = proto_inst
        proto_inst.on_start(input_buffer)
    
    send_to_server(input_buffer)

    if cmd_line_args.mode != None:
        name_to_protocol[cmd_line_args.mode].on_interact(input_buffer)

    send_to_server(input_buffer)

if __name__ == '__main__':
    ok_main(parse_input())
