"""This module supports various loading, dumping, and importing utilities."""

from client import exceptions
from client.models import core
from client.utils import formatting
import importlib
import os
import sys

#############
# Importing #
#############

def import_module(module):
    """Attempt to load the source file at path. Returns None on failure."""
    return importlib.import_module(module)

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
    sys.path.insert(0, os.path.abspath(test_dir))
    assignment = _get_info(case_map)
    _get_tests(test_dir, assignment, case_map)
    return assignment

def _get_info(case_map):
    """Loads information from an INFO file, given by the filepath.

    PARAMETERS:
    filepath -- str; filepath to an INFO file.

    RETURNS:
    dict; information contained in the INFO file.
    """
    # TODO(albert): add error handling in case no attribute info is
    # found.
    module_name, _ = os.path.splitext(INFO_FILE)
    info_json = import_module(module_name).info
    return core.Assignment.deserialize(info_json, case_map)

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
        module_name, _ = os.path.splitext(file)
        if os.path.isfile(path):
            try:
                test_json = import_module(module_name).test
                test = core.Test.deserialize(test_json, assignment, case_map)
                assignment.add_test(test)
            except AttributeError as ex:
                # TODO(soumya): Do something here, but only for staff protocols.
                pass

######################
# Assignment dumping #
######################

def dump_tests(test_dir, assignment, log=None):
    """Writes an assignment into the given test directory.

    PARAMETERS:
    test_dir   -- str; filepath to the assignment's test directory.
    assignment -- dict; contains information, including Test objects,
                  for an assignment.
    """
    # TODO(albert): prettyify string formatting by using triple quotes.
    # TODO(albert): verify that assign_copy is serializable into json.
    info = formatting.prettyjson(assignment.serialize())
    with open(os.path.join(test_dir, INFO_FILE), 'w') as f:
        if log:
            log.info('Dumping %s', INFO_FILE)
        f.write('info = ' + info)

    # TODO(albert): writing causes an error halfway, the tests
    # directory may be left in a corrupted state.
    # TODO(albert): might need to delete obsolete test files too.
    # TODO(albert): verify that test_json is serializable into json.
    for test in assignment.tests:
        test_json = formatting.prettyjson(test.serialize())
        with open(os.path.join(test_dir, test.name + '.py'), 'w') as f:
            if log:
                log.info('Dumping %s', test.name)
            f.write('test = ' + test_json)
