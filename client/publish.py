#! /usr/bin/env python3

"""
This module is responsible for publishing ok. This will put all of the
required files (as determined by config.py) into a separate directory
and then make a zipfile called 'ok' that can be distributed to students.
"""

import argparse
import config
import zipfile
import os
import shutil
from protocols import *
from models import *

STAGING_DIR = os.path.join(os.getcwd(), 'staging')

REQUIRED_FILES = [
    '__main__',
    'auth',
    'config',
    'exceptions',
    'ok',
    'utils',
]
REQUIRED_FOLDERS = [
    'sanction',
]

# Make the staging_dir
os.mkdir(STAGING_DIR)

def populate_staging(staging_dir):
    """Populates the staging directory with files for ok.py."""
    for filename in REQUIRED_FILES:
        fullname = filename + '.py'
        shutil.copyfile(fullname, os.path.join(staging_dir, fullname))

    for folder in REQUIRED_FOLDERS:
        shutil.copytree(folder, os.path.join(staging_dir, folder))

    populate_protocols(staging_dir)
    populate_models(staging_dir)

def populate_protocols(staging_dir):
    """Populates the protocols/ directory in the staging directory with
    relevant protocols.
    """
    os.mkdir(os.path.join(staging_dir, 'protocols'))
    shutil.copyfile(os.path.join('protocols', '__init__.py'),
                    os.path.join(staging_dir, 'protocols', '__init__.py'))
    shutil.copyfile(os.path.join('protocols', 'protocol.py'),
                    os.path.join(staging_dir, 'protocols', 'protocol.py'))

    for proto in protocol.get_protocols(config.protocols):
        # Split the module along pacakge delimiters, the '.'
        path_components = proto.__module__.split('.')
        # Convert to filesystem path.
        protocol_src = os.path.join(*path_components) + '.py'

        protocol_dest = os.path.join(staging_dir, protocol_src)
        if os.path.isfile(protocol_src):
            shutil.copyfile(protocol_src, protocol_dest)
        else:
            print('Unable to copy protocol {} from {}.'.format(
                  proto.name, protocol_src))

def populate_models(staging_dir):
    """Populates the models/ directory in the staging directory with
    relevant test cases.
    """
    os.mkdir(os.path.join(staging_dir, 'models'))
    shutil.copyfile(os.path.join('models', '__init__.py'),
                    os.path.join(staging_dir, 'models', '__init__.py'))
    shutil.copyfile(os.path.join('models', 'core.py'),
                    os.path.join(staging_dir, 'models', 'core.py'))
    shutil.copyfile(os.path.join('models', 'serialize.py'),
                    os.path.join(staging_dir, 'models', 'serialize.py'))

    for case in core.get_testcases(config.cases):
        # Split the module along pacakge delimiters, the '.'
        path_components = case.__module__.split('.')
        # Convert to filesystem path.
        case_src = os.path.join(*path_components) + '.py'

        case_dest = os.path.join(staging_dir, case_src)
        if os.path.isfile(case_src):
            shutil.copyfile(case_src, case_dest)
        else:
            print('Unable to copy test case {} from {}.'.format(
                  case.type, case_src))

def create_zip(staging_dir):
    zipf = zipfile.ZipFile('ok', 'w')
    for root, dirs, files in os.walk(staging_dir):
        if '__pycache__' in root:
            continue
        for filename in files:
            if filename.endswith('.pyc'):
                continue
            fullname = os.path.join(root, filename)
            # Replace 'staging' with '.' in the zip archive.
            arcname = fullname.replace(staging_dir, '.')
            zipf.write(fullname, arcname=arcname)
    zipf.close()

# Clean up staging dir
shutil.rmtree(STAGING_DIR)

def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-c', '--config', type=str,
                        help='Publish with a specificed config file.')
    parser.add_argument('-d', '--destination', type=str,
                        help='Publish to the specified directory.')

    return parser.parse_args()

def publish(args):
    if os.path.exists(STAGING_DIR):
        answer = input('{} already exists. Delete it? [y/n]: '.format(
                       STAGING_DIR))
        if answer.lower() in ('yes', 'y'):
            shutil.rmtree(STAGING_DIR)

    os.mkdir(STAGING_DIR)
    try:
        populate_staging(STAGING_DIR)
        create_zip(STAGING_DIR)
    finally:
        shutil.rmtree(STAGING_DIR)


def main():
    publish(parse_args())

if __name__ == '__main__':
    main()
