"""
Run server tests.

Usage:
"""

import sys, os
import unittest2
import warnings

# silences Python's complaints about imports
warnings.filterwarnings('ignore', category=UserWarning)

USAGE = """
FLASK_CONF=TEST python apptest.py [GAE_SDK]

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
    result = unittest2.TextTestRunner(verbosity=2).run(suite)

    if len(result.failures):
        return True
    return False


if __name__ == '__main__':
    # See: code.google.com/appengine/docs/python/tools/localunittesting.html
    try:
        # Path to the SDK installation
        if 'GAE_SDK' in os.environ:
            SDK_PATH = os.environ['GAE_SDK']
        else:
            SDK_PATH = sys.argv[1] # ...or hardcoded path
        # Path to tests folder
        dir_of_file = os.path.dirname(os.path.abspath(__file__))
        TEST_PATH = os.path.join(dir_of_file, 'tests')
        test_types = os.listdir(TEST_PATH)
        print(test_types)
        failed = False
        for typ in test_types:
            test_dir = os.path.join(TEST_PATH, typ)
            if not os.path.isdir(test_dir):
                continue
            print '='*60
            print "Doing {} testing".format(typ)
            print '='*60
            failed = main(SDK_PATH, TEST_PATH, test_dir) or failed
        sys.exit(int(failed))
    except IndexError:
        # you probably forgot about path as first argument
        print USAGE
