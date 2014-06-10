#! /usr/bin/python3

"""
Runs all tests for the client side autograder.
"""

import nose

nose.run(argv=['-w', './client/tests'])
