#! /usr/bin/env python3

"""
This module is responsible for publishing ok. This will put all of the
required files (as determined by config.py) into a separate directory
and then make a zipfile called "ok" that can be distributed to students.
"""

import os
OK_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.relpath(__file__)), '..'))  # Parent of cli/

from client.models import *
from client.protocols import *
import argparse
import importlib
import shutil
import sys
import zipfile

STAGING_DIR = os.path.join(os.getcwd(), 'staging')
OK_NAME = 'ok'
CONFIG_NAME = 'config.py'

REQUIRED_FILES = [
    '__init__',
    'exceptions',
]
REQUIRED_FOLDERS = [
    'utils',
]
COMMAND_LINE = [
    'ok',
]

def populate_staging(staging_dir, config_path):
    """Populates the staging directory with files for ok.py."""
    # Command line tools.
    os.mkdir(os.path.join(staging_dir, 'cli'))
    for filename in ['__init__'] + COMMAND_LINE:
        filename += '.py'
        fullname = os.path.join(OK_ROOT, 'cli', filename)
        shutil.copy(fullname, os.path.join(staging_dir, 'cli'))
    # Top-level files.
    for filename in REQUIRED_FILES:
        filename += '.py'
        fullname = os.path.join(OK_ROOT, filename)
        shutil.copyfile(fullname, os.path.join(staging_dir, filename))
    # Configuration file.
    shutil.copyfile(config_path, os.path.join(staging_dir, CONFIG_NAME))

    for folder in REQUIRED_FOLDERS:
        shutil.copytree(os.path.join(OK_ROOT, folder),
                        os.path.join(staging_dir, folder))

    config = load_config(config_path)
    populate_protocols(staging_dir, config)
    populate_models(staging_dir, config)

def load_config(filepath):
    """Loads the configuration file at the given filepath."""
    # TODO(albert): merge this import tool with the one in ok
    if not filepath:
        import config
        return config
    module_dir, module_name = os.path.split(os.path.abspath(filepath))
    sys.path.insert(0, module_dir)
    config = importlib.import_module(os.path.splitext(module_name)[0])
    sys.path.pop(0)
    return config

def populate_protocols(staging_dir, config):
    """Populates the protocols/ directory in the staging directory with
    relevant protocols.
    """
    os.mkdir(os.path.join(staging_dir, 'protocols'))
    shutil.copyfile(os.path.join(OK_ROOT, 'protocols', 'protocol.py'),
                    os.path.join(staging_dir, 'protocols', 'protocol.py'))

    protocol_modules = ['protocol']
    for proto in protocol.get_protocols(config.protocols):
        # Split the module along pacakge delimiters, the '.'
        path_components = proto.__module__.split('.')
        # Remove 'client' from path, since it's already part of OK_ROOT.
        path_components.pop(0)
        # Add the module to the list of imports in protocols/__init__
        protocol_modules.append(path_components[-1])
        # Convert to filesystem path.
        protocol_src = os.path.join(OK_ROOT, *path_components) + '.py'
        protocol_dest = os.path.join(staging_dir, *path_components) + '.py'

        if os.path.isfile(protocol_src):
            shutil.copyfile(protocol_src, protocol_dest)
        else:
            print('Unable to copy protocol {} from {}.'.format(
                proto.name, protocol_src))
    with open(os.path.join(staging_dir, 'protocols', '__init__.py'), 'w') as f:
        f.write('__all__ = {}'.format(protocol_modules))

def populate_models(staging_dir, config):
    """Populates the models/ directory in the staging directory with
    relevant test cases.
    """
    os.mkdir(os.path.join(staging_dir, 'models'))
    shutil.copyfile(os.path.join(OK_ROOT, 'models', 'core.py'),
                    os.path.join(staging_dir, 'models', 'core.py'))
    shutil.copyfile(os.path.join(OK_ROOT, 'models', 'serialize.py'),
                    os.path.join(staging_dir, 'models', 'serialize.py'))

    case_modules = ['core', 'serialize']
    for case in core.get_testcases(config.cases):
        # Split the module along pacakge delimiters, the '.'
        path_components = case.__module__.split('.')
        # Remove 'client' from path, since it's already part of OK_ROOT.
        path_components.pop(0)
        # Add the module to the list of imports in models/__init__
        case_modules.append(path_components[-1])
        # Convert to filesystem path.
        case_src = os.path.join(OK_ROOT, *path_components) + '.py'
        case_dest = os.path.join(staging_dir, *path_components) + '.py'

        if os.path.isfile(case_src):
            shutil.copyfile(case_src, case_dest)
        else:
            print('Unable to copy test case {} from {}.'.format(
                case.type, case_src))
    with open(os.path.join(staging_dir, 'models', '__init__.py'), 'w') as f:
        f.write('__all__ = {}'.format(case_modules))

def create_zip(staging_dir, destination):
    if not os.path.isdir(destination):
        os.mkdir(destination)

    dest = os.path.join(destination, OK_NAME)
    zipf = zipfile.ZipFile(dest, 'w')
    zipf.write(os.path.join(OK_ROOT, '__main__.py'), './__main__.py')
    for root, _, files in os.walk(staging_dir):
        if '__pycache__' in root:
            continue
        for filename in files:
            if filename.endswith('.pyc'):
                continue
            fullname = os.path.join(root, filename)
            # Replace 'staging' with './client' in the zip archive.
            arcname = fullname.replace(staging_dir, './client')
            zipf.write(fullname, arcname=arcname)
    zipf.close()

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-c', '--config', type=str,
                        default=os.path.join(OK_ROOT, CONFIG_NAME),
                        help='Publish with a specificed config file.')
    parser.add_argument('-d', '--destination', type=str, default='.',
                        help='Publish to the specified directory.')

    return parser.parse_args()

def publish(args):
    if os.path.exists(STAGING_DIR):
        answer = input('{} already exists. Delete it? [y/n]: '.format(
            STAGING_DIR))
        if answer.lower() in ('yes', 'y'):
            shutil.rmtree(STAGING_DIR)
        else:
            print('Aborting publishing.')
            exit(1)

    os.mkdir(STAGING_DIR)
    try:
        populate_staging(STAGING_DIR, args.config)
        create_zip(STAGING_DIR, args.destination)
    finally:
        shutil.rmtree(STAGING_DIR)


def main():
    publish(parse_args())

if __name__ == '__main__':
    main()
