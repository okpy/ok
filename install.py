#!/usr/bin/env python3

"""Create virtualenvs, set up git hooks, install dependencies, etc.

Run this script with no arguments initially and whenever dependencies change.

Individual zero-arg functions from this file can be called by passing their
names as command-line arguments. E.g., 'python3 install.py check_pythons'.
"""

import os
import subprocess
import sys
import shutil

def main():
    check_pythons()
    check_gae()
    setup_envs()
    shell_with_env('server', 'pip install -r server_requirements.txt')
    shell_with_env('server', 'server/app/generate_keys.py')
    run_linkenv()
    symlink_git_hooks()

ENV_DIR = 'env'

def call(fn_name):
    """Call fn with fn_name (str) using no arguments."""
    if fn_name not in globals():
        raise Exception('No function named "{}"'.format(fn_name))
    fn = globals()[fn_name]
    if not callable(fn):
        raise Exception('"{}" bound to uncallable {}'.format(fn_name, fn))
    fn.__call__()

def shell(*args):
    """Call shell command and return its stderr. args are space-separated."""
    cmd = ' '.join(args)
    print('$', cmd)
    stdout = subprocess.check_output(cmd, shell=True, executable='/bin/bash')
    stdout_str = stdout.decode('utf-8').strip()
    print(stdout_str)
    return stdout_str

def which(exe):
    """Return the path to an executable or None."""
    if hasattr(shutil, 'which'):
        return shutil.which(exe)
    else:
        return shell('which', exe)

def shell_with_env(env_name, *args):
    """Call shell command within an activated virtualenv."""
    env = os.path.join(ENV_DIR, env_name)
    if not os.path.exists(os.path.join(env, 'bin', 'activate')):
        raise Exception('No activate found for "{}"'.format(env))
    cmd = 'source ' + env + '/bin/activate;' + ' '.join(args) + ';deactivate'
    return shell(cmd)

def check_pythons():
    """Check Python versions."""
    version_list = lambda version_str: [int(n) for n in version_str.split('.')]
    for python, min_version in [('python', '2.7')]:
        if which(python) is None:
            raise Exception('Command "{}" not found')
        redirect_err_to_out = '2>&1'
        version = shell(python, '--version', redirect_err_to_out).split()[1]
        version = version.replace('+', '')
        if version_list(version) < version_list(min_version):
            raise Exception('"{}" version {} is older than minimum {}'.format(
                python, version, min_version))

def check_gae():
    """Check that Google App Engine SDK is installed and linked."""
    if 'GAE_SDK' not in os.environ:
        raise Exception('GAE_SDK not defined. Is App Engine installed?')
    print('GAE_SDK found')

def setup_envs():
    """Set up virtual environments for each part of the system."""
    client, server = [os.path.join(ENV_DIR, d) for d in ('client', 'server')]
    for env_path, python in [(server, 'python')]:
        if not os.path.exists(os.path.join(env_path, 'bin')):
            shell('virtualenv', '-p', which(python), env_path)
    print('Virtual environments are created')

def run_linkenv():
    """Call linkenv to set up appengine dependencies."""
    shell_with_env('server', 'python', '-m', 'linkenv.linkenv',
                   'env/server/lib/python2.7/site-packages',
                   'server/gaenv', '1>/dev/null')

def symlink_git_hooks():
    """Add symlink to hooks in .git."""
    if not os.path.exists('.git/hooks/pre-commit'):
        os.symlink('../../hooks/pre-commit.py', '.git/hooks/pre-commit')

if __name__ == '__main__':
    # If there are command-line arguments, call the named functions.
    if len(sys.argv) > 1:
        for fn_name in sys.argv[1:]:
            call(fn_name)
    else:
        main()




