"""Tests for hw1 demo assignment."""

# General information about the assignment
assignment = {
  'name': 'hw1',
  'src_files': ['hw1.py'],
  'version': '1.0',
}

# Information that is needed by different types of test cases to set up
setup = {
  # For doctest-style tests, this setup is run only once, and is stored
  # in a frame (dictionary). Each test case will be evaluated in a
  # copy of that frame. Thus, any computationally expensive code that
  # should only be run once can be put here.
  'doctest': """
  >>> from hw1 import *
  """
}
