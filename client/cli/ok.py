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
from client import config
from client import exceptions
from client.models import *
from client.protocols import *
from client.utils import auth
from client.utils import loading
from client.utils import network
from client.utils import output
from datetime import datetime
from urllib import error
import argparse
import client
import os
import pickle
import sys
import logging

BACKUP_FILE = ".ok_messages"
LOGGING_FORMAT = '%(levelname)-10s | pid %(process)d | %(filename)s, line %(lineno)d: %(message)s'

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
    parser.add_argument('-s', '--server', type=str,
                        default='ok-server.appspot.com',
                        help="server address")
    parser.add_argument('-t', '--tests', metavar='A', default='tests', type=str,
                        help="partial name or path to test file or directory")
    parser.add_argument('-u', '--unlock', action='store_true',
                        help="unlock tests interactively")
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="print more output")
    parser.add_argument('--debug', action='store_true',
                        help="show debug statements")
    parser.add_argument('--insecure', action='store_true',
                        help="uses http instead of https")
    parser.add_argument('-i', '--interactive', action='store_true',
                        help="toggle interactive mode")
    parser.add_argument('-l', '--lock', type=str,
                        help="partial path to directory to lock")
    parser.add_argument('--submit', action='store_true',
                        help="wait for server response without timeout")
    parser.add_argument('-a', '--authenticate', action='store_true',
                        help="authenticate, ignoring previous authentication")
    parser.add_argument('--local', action='store_true',
                        help="disable any network activity")
    parser.add_argument('--timeout', type=int, default=10,
                        help="set the timeout duration for running tests")
    parser.add_argument('--version', action='store_true',
                        help="Prints the version number and quits")
    parser.add_argument('--score', action='store_true',
                        help="Scores the assignment")
    return parser.parse_args()

def main():
    """Run all relevant aspects of ok.py."""
    args = parse_input()

    logging.basicConfig(format=LOGGING_FORMAT)
    log = logging.getLogger(__name__)
    if args.debug:
        log.setLevel(logging.INFO)
    else:
        log.setLevel(logging.ERROR)

    log.info(args)

    if args.version:
        print("okpy=={}".format(client.__version__))
        exit(0)

    if not args.local and not args.insecure:
        try:
            import ssl
        except:
            log.warning('Error importing ssl', stack_info=True)
            sys.exit("SSL Bindings are not installed. You can install python3 SSL bindings or \nrun ok locally with python3 ok --local")


    server_thread, timer_thread = None, None
    try:
        print("You are running version {0} of ok.py".format(client.__version__))

        cases = {case.type: case for case in core.get_testcases(config.cases)}
        assignment = None
        try:
            assignment = loading.load_tests(args.tests, cases)
        except exceptions.OkException as e:
            print('Error:', e)
            exit(1)

        log.info('Replacing stdout with OutputLogger')
        output_logger = sys.stdout = output.OutputLogger()

        log.info('Instantiating protocols')
        protocols = [p(args, assignment, output_logger, log)
                     for p in protocol.get_protocols(config.protocols)]

        messages = dict()
        msg_list= []

        try:
            with open(BACKUP_FILE, 'rb') as fp:
                msg_list = pickle.load(fp)
                log.info('Loaded %d backed up messages from %s',
                         len(msg_list), BACKUP_FILE)
        except (IOError, EOFError) as e:
            log.info('Error reading from ' + BACKUP_FILE \
                    + ', assume nothing backed up')

        for proto in protocols:
            log.info('Execute %s.on_start()', proto.name)
            messages[proto.name] = proto.on_start()
        messages['timestamp'] = str(datetime.now())

        interact_msg = {}

        for proto in protocols:
            log.info('Execute %s.on_interact()', proto.name)
            interact_msg[proto.name] = proto.on_interact()

        interact_msg['timestamp'] = str(datetime.now())

        # TODO(denero) Print server responses.

        if not args.local:
            msg_list.append(interact_msg)

            try:
                access_token = auth.authenticate(args.authenticate)
                log.info('Authenticated with access token %s', access_token)

                msg_list.append(messages)
                print("Attempting to send files to server...")
                network.dump_to_server(access_token, msg_list,
                        assignment['name'], args.server, args.insecure,
                        client.__version__, log, send_all=args.submit)

            except error.URLError as ex:
                log.warning('on_start messages not sent to server: %s', str(e))

            with open(BACKUP_FILE, 'wb') as fp:
                log.info('Save %d unsent messages to %s', len(msg_list),
                         BACKUP_FILE)

                pickle.dump(msg_list, fp)
                os.fsync(fp)

            if len(msg_list) == 0:
                print("Server submission successful")

    except KeyboardInterrupt:
        print("Quitting ok.")

    finally:
        if assignment:
            log.info('Dump tests for %s to %s', assignment['name'], args.tests)
            loading.dump_tests(args.tests, assignment, log)

if __name__ == '__main__':
    main()
