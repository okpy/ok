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

def main(sdk_path, test_path):
    sys.path.insert(0, sdk_path)
    import dev_appserver
    dev_appserver.fix_sys_path()
    sys.path.insert(1, os.path.join(os.path.abspath('.'), 'lib'))
    suite = unittest2.loader.TestLoader().discover(test_path)
    result = unittest2.TextTestRunner(verbosity=2).run(suite)
    if len(result.failures):
        sys.exit(1)
    sys.exit(0)


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
        main(SDK_PATH, TEST_PATH)
    except IndexError:
        # you probably forgot about path as first argument
        print USAGE
