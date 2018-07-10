#!/usr/bin/env python
"""Script to convert all the current environment variables into the envdir
format.
"""

import os


def env_to_envdir(to_dir):
    for env_key, env_value in os.environ.items():
        env_file = os.path.join(to_dir, env_key)
        with open(env_file, 'wb') as fobj:
            fobj.write(env_value.encode('utf-8'))


if __name__ == '__main__':
    import argparse
    import tempfile

    parser = argparse.ArgumentParser(usage=__doc__)
    parser.add_argument('--envdir')
    args = parser.parse_args()

    if args.envdir:
        env_dir = args.envdir
    else:
        env_dir = tempfile.mkdtemp()

    env_to_envdir(env_dir)

    if not args.envdir:
        print(env_dir)
