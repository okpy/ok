#!/usr/bin/python3
VERSION = '1.0.6'

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

from auth import authenticate
from models import core
from urllib import request, error
from utils import formatting
from utils import output
import argparse
import base64
import config
import exceptions
import importlib.machinery
import json
import multiprocessing
import os
import sys
import time

def send_to_server(access_token, messages, assignment, server, endpoint='submission'):
    """Send messages to server, along with user authentication."""
    assignment = core.Assignment.deserialize(assignment)
    data = {
        'assignment': assignment['name'],
        'messages': messages,
    }
    try:
        address = 'https://' + server + '/api/v1/' + endpoint
        serialized = json.dumps(data).encode(encoding='utf-8')
        # TODO(denero) Wrap in timeout (maybe use PR #51 timed execution).
        # TODO(denero) Send access token with the request
        address += "?access_token=%s&client_version=%s" % (access_token, VERSION)
        req = request.Request(address)
        req.add_header("Content-Type", "application/json")
        response = request.urlopen(req, serialized)
        return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as ex:
        # print("Error while sending to server: {}".format(ex))
        try:
            #response_json = json.loads(response)
            if ex.code == 403:
                get_latest_version(server)
            #message = response_json['message']
            #indented = '\n'.join('\t' + line for line in message.split('\n'))
            #print(indented)
            return {}
        except Exception as e:
            # print(e)
            # print("Couldn't connect to server")
            pass



#####################
# Software Updating #
#####################

def get_latest_version(server):
    """Check for the latest version of ok and update this file accordingly.
    """
    #print("We detected that you are running an old version of ok.py: {0}".format(VERSION))

    # Get server version
    address = "https://" + server + "/api/v1" + "/version?name=okpy"

    try:
        #print("Updating now...")
        req = request.Request(address)
        response = request.urlopen(req)

        full_response = json.loads(response.read().decode('utf-8'))

        file_contents = base64.b64decode(full_response['data']['results'][0]['file_data'])
        new_file = open('ok', 'wb')
        new_file.write(file_contents)
        new_file.close()
        #print("Done updating!")
    except error.HTTPError as ex:
        # print("Error when downloading new version")
        pass

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
    parser.add_argument('-s', '--server', type=str, default='ok-server.appspot.com',
                        help="server address")
    parser.add_argument('-t', '--tests', metavar='A', default='tests', type=str,
                        help="partial name or path to test file or directory")
    parser.add_argument('-u', '--unlock', action='store_true',
                        help="unlock tests interactively")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="print more output")
    parser.add_argument('-i', '--interactive', action='store_true',
                        help="toggle interactive mode")
    parser.add_argument('-l', '--lock', type=str,
                        help="partial name or path to test file or directory to lock")
    parser.add_argument('-f', '--force', action='store_true',
                        help="force waiting for a server response without timeout")
    parser.add_argument('-a', '--authenticate', action='store_true',
                        help="authenticate, ignoring previous authentication")
    parser.add_argument('--local', action='store_true',
                        help="disable any network activity")
    parser.add_argument('--timeout', type=int, default=10,
                        help="set the timeout duration for running tests")
    return parser.parse_args()


def server_timer():
    time.sleep(0.8)

def ok_main(args):
    """Run all relevant aspects of ok.py."""
    server_thread, timer_thread = None, None
    try:
        print("You are running version {0} of ok.py".format(VERSION))
        if not args.local:
            timer_thread = multiprocessing.Process(target=server_timer, args=())
            timer_thread.start()
        assignment = load_tests(args.tests, config.cases)

        logger = sys.stdout = output.OutputLogger()

        start_protocols = \
            [p(args, assignment, logger) for p in config.protocols.values()]
        interact_protocols = \
            [p(args, assignment, logger) for p in config.protocols.values()]

        messages = dict()

        for protocol in start_protocols:
            messages[protocol.name] = protocol.on_start()

        if not args.local:
            try:
                access_token = authenticate(args.authenticate)
                server_thread = multiprocessing.Process(target=send_to_server, args=(access_token, messages, assignment.serialize(), args.server))
                server_thread.start()
            except error.URLError as ex:
                # TODO(soumya) Make a better error message
                # print("Nothing was sent to the server!")
                pass

        for protocol in interact_protocols:
            protocol.on_interact()

        # TODO(denero) Print server responses.

        # TODO(albert): a premature error might prevent tests from being
        # dumped. Perhaps add this in a "finally" clause.
        dump_tests(args.tests, assignment)

        if not args.local:
            while timer_thread.is_alive():
                pass

            if not args.force:
                server_thread.terminate()

    except KeyboardInterrupt:
        if timer_thread:
            timer_thread.terminate()
        if server_thread:
            server_thread.terminate()

if __name__ == '__main__':
    ok_main(parse_input())
