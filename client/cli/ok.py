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
BACKUP_FILE = ".ok_messages"

from client import config
from client.models import *
from client.protocols import *
from client.utils import auth
from client.utils import loading
from client.utils import output
from datetime import datetime
from urllib import request, error
import client
import argparse
import base64
import json
import multiprocessing
import pickle
import sys
import time

def send_to_server(access_token, messages, name, server,
                   insecure=False):
    """Send messages to server, along with user authentication."""
    data = {
        'assignment': name,
        'messages': messages,
    }
    try:
        prefix = "http" if insecure else "https"
        address = prefix + '://' + server + '/api/v1/submission'
        serialized = json.dumps(data).encode(encoding='utf-8')
        # TODO(denero) Wrap in timeout (maybe use PR #51 timed execution).
        # TODO(denero) Send access token with the request
        address += "?access_token={0}&client_version={1}".format(
            access_token, client.__version__)
        req = request.Request(address)
        req.add_header("Content-Type", "application/json")
        response = request.urlopen(req, serialized)
        return json.loads(response.read().decode('utf-8'))
    except error.HTTPError as ex:
        # print("Error while sending to server: {}".format(ex))
        try:
            if ex.code == 403:
                response = ex.read().decode('utf-8')
                response_json = json.loads(response)
                get_latest_version(response_json['data']['download_link'])
            #message = response_json['message']
            #indented = '\n'.join('\t' + line for line in message.split('\n'))
            #print(indented)
            return {}
        except Exception as e:
            # print(e)
            # print("Couldn't connect to server")
            pass

def dump_to_server(access_token, msg_queue, name, server, insecure, staging_queue):
    while not msg_queue.empty():
        message = msg_queue.get()
        staging_queue.put(message)
        try:
            if send_to_server(access_token, message, name, server, insecure) == None:
                staging_queue.get() #throw away successful message
        except error.URLError as ex:
            pass
    return

#####################
# Software Updating #
#####################

def get_latest_version(download_link):
    """Check for the latest version of ok and update this file accordingly.
    """
    #print("We detected that you are running an old version of ok.py: {0}".format(VERSION))

    # Get server version

    try:
        req = request.Request(download_link)
        response = request.urlopen(req)

        zip_binary = response.read()
        with open('ok', 'wb') as f:
            f.write(zip_binary)
        #print("Done updating!")
    except error.HTTPError:
        # print("Error when downloading new version")
        pass

##########################
# Command-line Interface #
##########################

def parse_input(protocol_list):
    """Parses command line input."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-q', '--question', type=str,
                        help="focus on a specific question")
    parser.add_argument('-s', '--server', type=str,
                        default='ok-server.appspot.com',
                        help="server address")
    parser.add_argument('-t', '--tests', metavar='TESTS_DIR', default='tests', type=str,
                        help="path to test directory")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="print more output")
    parser.add_argument('--insecure', action='store_true',
                        help="uses http instead of https")
    parser.add_argument('-f', '--force', action='store_true',
                        help="wait for server response without timeout")
    parser.add_argument('-a', '--authenticate', action='store_true',
                        help="authenticate, ignoring previous authentication")
    parser.add_argument('--local', action='store_true',
                        help="disable any network activity")
    parser.add_argument('--timeout', type=int, default=10,
                        help="set the timeout duration for running tests")
    parser.add_argument('--version', action='store_true',
                        help="Prints the version number and quits")

    # Add protocol-specific arguments
    for proto in protocol_list:
        proto.add_args(parser)

    return parser.parse_args()

def server_timer():
    """Timeout for the server."""
    time.sleep(0.8)

def main():
    """Run all relevant aspects of ok.py."""
    protocol_list = protocol.get_protocols(config.protocols)

    args = parse_input(protocol_list)

    if args.version:
        print("okpy=={}".format(client.__version__))
        exit(0)

    if not args.local and not args.insecure:
        try:
            import ssl
        except: 
            sys.exit("SSL Bindings are not installed. You can install python3 SSL bindings or \nrun ok locally with python3 ok --local")


    server_thread, timer_thread = None, None
    try:
        print("You are running version {0} of ok.py".format(client.__version__))
        if not args.local:
            timer_thread = multiprocessing.Process(target=server_timer, args=())
            timer_thread.start()
        cases = {case.type: case for case in core.get_testcases(config.cases)}
        assignment = loading.load_tests(args.tests, cases)

        logger = sys.stdout = output.OutputLogger()

        protocols = [p(args, assignment, logger) for p in protocol_list]

        messages = dict()
        msg_queue = multiprocessing.Queue()
        file_contents = []

        try:
            with open(BACKUP_FILE, 'rb') as fp:
                file_contents = pickle.load(fp)
        except IOError as e:
            # File doesn't exist, so file_contents should be empty
            pass
        except EOFError as e:
            # File is empty, so no messages are inside
            pass

        for message in file_contents:
            msg_queue.put(message)

        for proto in protocols:
            messages[proto.name] = proto.on_start()
        messages['timestamp'] = str(datetime.now())

        if not args.local:
            try:
                access_token = auth.authenticate(args.authenticate)
                msg_queue.put(messages)
                staging_queue = multiprocessing.Queue()
                server_thread = multiprocessing.Process(
                    target=dump_to_server,
                    args=(access_token, msg_queue, assignment['name'],
                          args.server, args.insecure, staging_queue))
                server_thread.start()
            except error.URLError as ex:
                # TODO(soumya) Make a better error message
                # print("Nothing was sent to the server!")
                pass
        
        interact_msg = {}

        for proto in protocols:
            interact_msg[proto.name] = proto.on_interact()

        interact_msg['timestamp'] = str(datetime.now())

        # TODO(denero) Print server responses.

        # TODO(albert): a premature error might prevent tests from being
        # dumped. Perhaps add this in a "finally" clause.
        loading.dump_tests(args.tests, assignment)

        if not args.local:
            msg_queue.put(interact_msg)
            
            while timer_thread.is_alive():
                pass

            if not args.force:
                server_thread.terminate()
            else:
                server_thread.join()

            dump_list = []
            while not msg_queue.empty():
                dump_list.append(msg_queue.get_nowait())
            while not staging_queue.empty():
                dump_list.append(staging_queue.get_nowait())
            with open(BACKUP_FILE, 'wb') as fp:
                pickle.dump(dump_list, fp)

    except KeyboardInterrupt:
        if timer_thread:
            timer_thread.terminate()
        if server_thread:
            server_thread.terminate()

if __name__ == '__main__':
    main()
