#!/usr/bin/python3
VERSION = '1.0.0'

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
import argparse
import config
import exceptions
import importlib.machinery
import json
import os
import sys
import utils
import multiprocessing
import base64
import time

def send_to_server(access_token, messages, assignment, server, endpoint='submission'):
    """Send messages to server, along with user authentication."""
    data = {
        'assignment': assignment['name'],
        'messages': messages,
    }
    try:
        print("Sending stuff to server...")
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
        print("Error while sending to server: {}".format(ex))
        try:
            #response_json = json.loads(response)
            if ex.code == 403:
                get_latest_version(server)
            #message = response_json['message']
            #indented = '\n'.join('\t' + line for line in message.split('\n'))
            #print(indented)
            return {}
        except Exception as e:
            print(e)
            print("Couldn't connect to server")


######################
# Assignment loading #
######################

INFO_FILE = 'info.py'

def load_tests(test_dir, case_map):
    """Loads information and tests for the current assignment.

    PARAMETERS:
    test_dir -- str; a filepath to the test directory, 'tests' by default.
    case_map -- dict; a mapping of TestCase tags to TestCase classes

    RETURNS:
    assignment -- Assignment; contains information related to the
    assignment and its tests.
    """
    if not os.path.isdir(test_dir):
        raise exceptions.OkException(
                'Assignment must have a {} directory'.format(test_dir))
    info_file = os.path.join(test_dir, INFO_FILE)
    if not os.path.isfile(info_file):
        raise exceptions.OkException(
                'Directory {} must have a file called {}'.format(
                    test_dir, INFO_FILE))
    assignment = _get_info(info_file)
    _get_tests(test_dir, assignment, case_map)
    return assignment


def _get_info(filepath):
    """Loads information from an INFO file, given by the filepath.

    PARAMETERS:
    filepath -- str; filepath to an INFO file.

    RETURNS:
    dict; information contained in the INFO file.
    """
    # TODO(albert): add error handling in case no attribute info is
    # found.
    info_json = _import_module(filepath).info
    return core.Assignment.deserialize(info_json)


def _get_tests(directory, assignment, case_map):
    """Loads all tests in a tests directory and adds them to the given
    Assignment object.

    PARAMETER:
    directory  -- str; filepath to a directory that contains tests.
    assignment -- Assignment; top-level information about the
                  assignment, extracted from the info file.
    """
    test_files = os.listdir(directory)
    # TODO(albert): have a better way to sort tests.
    for file in sorted(test_files):
        if file == INFO_FILE or not file.endswith('.py'):
            continue
        path = os.path.normpath(os.path.join(directory, file))
        if os.path.isfile(path):
            try:
                test_json = _import_module(path).test
                test = core.Test.deserialize(test_json, assignment, case_map)
                assignment.add_test(test)
            except AttributeError as ex:
                # TODO(soumya): Do something here, but only for staff protocols.
                pass


def _import_module(path):
    """Attempt to load the source file at path. Returns None on failure."""
    loader = importlib.machinery.SourceFileLoader(path, path)
    test_module = loader.load_module()
    return test_module

######################
# Assignment dumping #
######################

def dump_tests(test_dir, assignment):
    """Writes an assignment into the given test directory.

    PARAMETERS:
    test_dir   -- str; filepath to the assignment's test directory.
    assignment -- dict; contains information, including Test objects,
                  for an assignment.
    """
    # TODO(albert): prettyify string formatting by using triple quotes.
    # TODO(albert): verify that assign_copy is serializable into json.
    info = utils.prettyformat(assignment.serialize())
    with open(os.path.join(test_dir, INFO_FILE), 'w') as f:
        f.write('info = ' + info)

    # TODO(albert): writing causes an error halfway, the tests
    # directory may be left in a corrupted state.
    # TODO(albert): might need to delete obsolete test files too.
    # TODO(albert): verify that test_json is serializable into json.
    for test in assignment.tests:
        test_json = utils.prettyformat(test.serialize())
        with open(os.path.join(test_dir, test.name + '.py'), 'w') as f:
            f.write('test = ' + test_json)

#####################
# Software Updating #
#####################

def get_latest_version(server):
    """Check for the latest version of ok and update this file accordingly.
    """
    print("You are running version {0} of ok.py".format(VERSION))

    # Get server version
    address = "https://" + server + "/api/v1" + "/version?name=okpy"

    try:
        req = request.Request(address)
        response = request.urlopen(req)

        full_response = json.loads(response.read().decode('utf-8'))

        file_contents = base64.b64decode(full_response['data']['results'][0]['file_data'])
        new_file = open('ok', 'wb')
        new_file.write(file_contents)
        new_file.close()
    except error.HTTPError as ex:
        print("Error when downloading new version")

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
                        help="toggles interactive mode")
    parser.add_argument('-l', '--lock', type=str,
                        help="partial name or path to test file or directory to lock")
    return parser.parse_args()


def ok_main(args):
    """Run all relevant aspects of ok.py."""
    timer_thread = multiprocessing.Process(target=lambda: time.sleep(0.8), args=())
    timer_thread.start()
    assignment = load_tests(args.tests, config.cases)

    # TODO(soumya): uncomment this once ok.py is ready to ship, to hide
    # error messages.
    # try:
    #     assignment = load_tests(args.tests, config.cases)
    # except Exception as ex:
    #     print(ex)
    #     sys.exit(1)

    logger = sys.stdout = utils.OutputLogger()

    start_protocols = \
        [p(args, assignment, logger) for p in config.protocols.values()]
    interact_protocols = \
        [p(args, assignment, logger) for p in config.protocols.values()]

    messages = dict()

    for protocol in start_protocols:
        messages[protocol.name] = protocol.on_start()

    try:
        access_token = authenticate()
        server_thread = multiprocessing.Process(target=send_to_server, args=(access_token, messages, assignment, args.server))
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

    while timer_thread.is_alive():
        pass

    server_thread.terminate()

if __name__ == '__main__':
    ok_main(parse_input())
