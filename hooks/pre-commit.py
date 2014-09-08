#!/usr/bin/env python
import sys

USE_PYLINT = True

try:
    from git_pylint_commit_hook import commit_hook
except ImportError:
    USE_PYLINT = False

def main():
    if USE_PYLINT:
        result = commit_hook.check_repo(9, "pylint", ".pylintrc", "-r y")
        if not result:
            sys.exit(1)

if __name__ == '__main__':
    main()
    sys.exit(0)
