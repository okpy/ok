from client.models import *
from client.protocols import unlock
from client.utils import loading
from client.utils import output
from client import config
import argparse
import sys

def parse_input():
    """Parses command line input."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-t', '--tests', type=str, default='tests',
                        help="Path to a specific directory of tests")
    return parser.parse_args()

def main():
    """Run the LockingProtocol."""
    args = parse_input()
    args.lock = True
    cases = {case.type: case for case in core.get_testcases(config.cases)}
    assignment = loading.load_tests(args.tests, cases)

    logger = sys.stdout = output.OutputLogger()

    protocol = unlock.LockProtocol(args, assignment, logger)
    protocol.on_start()

    loading.dump_tests(args.tests, assignment)

if __name__ == '__main__':
    main()
