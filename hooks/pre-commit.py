#!/usr/bin/env python
import sys

from git_pylint_commit_hook import commit_hook

def main():
    result = commit_hook.check_repo(9, "pylint", ".pylintrc", "")
    if result:
        sys.exit(0)
    sys.exit(1)

if __name__ == '__main__':
    main()
    sys.exit(0)
