"""
Autograder locking script

This file locks tests associated with a specified project. The
resulting locked tests are intended for student use.
"""

import argparse
import hmac
import importlib
import os
import pickle
import random
import string
alphabet = string.ascii_lowercase + string.digits

#######################
# Unlocking Mechanism #
#######################

def gen_key():
    return ''.join(random.choice(alphabet) for _ in range(128))

def hash_fn(hash_key, x):
    return hmac.new(hash_key.encode('utf-8'), x.encode('utf-8')).digest()

def fetch_key(module_name):
    return importlib.import_module(module_name).project_info['hash_key']

def lock_case(case, key, no_lock):
    if len(case) == 2:
        case.append('')
    status = ''
    if no_lock or 'unlock' in case[2]:
        status += 'unlock'
    if 'concept' in case[2]:
        status += 'concept'
    case[2] = status
    if type(case[1]) in (str, tuple):
        case[1] = [case[1]]
    if 'unlock' in status:
        return

    for i, answer in enumerate(case[1]):
        if type(answer) == str:
            case[1][i] = hash_fn(key, answer)

def lock_all_tests(project, test_module, dest=''):
    """Locks all tests for a given project.

    PARAMETERS:
    project     -- str; name of project
    test_module -- module; contains tests for the project
    dest        -- str; filepath for destination. If dest is the empty
                   string, defaults to the current working directory

    DESCRIPTION:
    This function locks the outputs of all tests in the given module.
    Locking is achieved by generating a random 128-byte key and using
    that key to hash each output.

    Two files will be written to the specified destination:
    locked_tests.py   -- contains two variables: tests, all of the
                         locked tests, and hash_key (this is the same
                         key used to lock)
    unlocked_tests.py -- contains two variables: tests, all unlocked
                         tests, and project_info
    """
    # hash_key = gen_key()
    hash_key = test_module.project_info['hash_key']

    # setup code for all tests
    preamble = test_module.preamble if hasattr(test_module, 'preamble') else ''
    cache = test_module.cache if hasattr(test_module, 'cache') else ''

    for test in test_module.tests:
        if 'suites' not in test:
            test['suites'] = []
            continue
        no_lock = hasattr(test_module, 'no_lock') and \
                any(map(lambda n: n in test_module.no_lock, test['name']))
        for suite in test['suites']:
            for case in suite:
                lock_case(case, hash_key, no_lock)

    test_filename = 'tests.pkl'
    if dest != '':
        test_filename = os.path.join(dest, test_filename)
    with open(test_filename, 'wb') as test_file:
        pickle.dump({
            'tests': test_module.tests,
            'project_info': test_module.project_info,
            'preamble': preamble,
            'cache': cache,
        }, test_file, pickle.DEFAULT_PROTOCOL)

##########################
# Command Line Interface #
##########################

def main():
    parser = argparse.ArgumentParser(
                description='Locking mechanism for 61A projects')
    parser.add_argument('project', type=str,
                        help='Name of the project. Expects {ASSIGN}_grader.py in the current directory')
    parser.add_argument('-d', '--destination', default='',
                        help='The destination for compiled files')
    args = parser.parse_args()
    tests = importlib.import_module('{}_grader'.format(args.project))
    lock_all_tests(args.project, tests, args.destination)

if __name__ == '__main__':
    main()
