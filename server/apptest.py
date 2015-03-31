"""
Run server tests.

Usage:
"""

import sys, os
import unittest2
import warnings
import argparse

# silences Python's complaints about imports
warnings.filterwarnings('ignore', category=UserWarning)

USAGE = """
You may add the path to your appengine SDK as an argument.
Otherwise, it is loaded from GAE_SDK.

Loading configuration depending on the value of
environment variable allows you to add your own
testing configuration in app/settings.py
"""


def main(sdk_path, test_root, test_path):
    """
    Runs the tests in the |test_path| directory.
    Returns if these tests failed or succeeded.
    """
    sys.path.insert(0, sdk_path)
    sys.path.insert(0, test_root)
    import dev_appserver
    dev_appserver.fix_sys_path()
    sys.path.insert(1, os.path.join(os.path.abspath('.'), 'lib'))
    suite = unittest2.loader.TestLoader().discover(test_path)
    result = unittest2.TextTestRunner(verbosity=1).run(suite)

    if result.failures or result.errors:
        return True
    return False


if __name__ == '__main__':
    # See: code.google.com/appengine/docs/python/tools/localunittesting.html
    parser = argparse.ArgumentParser(description=USAGE)
    parser.add_argument(
        '--sdk_location', type=str, default=os.environ.get('GAE_SDK'))
    parser.add_argument(
        '--quiet', action='store_true',
        help="Disables logging output from the tests.")
    args = parser.parse_args()

    if args.quiet:
        from app import urls
        urls.logging.disable(urls.logging.exception)

    if not args.sdk_location:
        parser.print_help()
        sys.exit(1)
    SDK_PATH = args.sdk_location

    # Path to tests folder
    dir_of_file = os.path.dirname(os.path.abspath(__file__))
    TEST_PATH = os.path.join(dir_of_file, 'tests')
    test_types = os.listdir(TEST_PATH)
    failed = False

    for typ in test_types:
        test_dir = os.path.join(TEST_PATH, typ)
        if not os.path.isdir(test_dir):
            continue
        print '='*60
        print "Doing {} testing".format(typ)
        print '='*60
        failed = main(SDK_PATH, TEST_PATH, test_dir) or failed
    if not failed:
        print "ALL TESTS PASSED"
    else:
        print "SOME TESTS FAILED"
    sys.exit(int(failed))
