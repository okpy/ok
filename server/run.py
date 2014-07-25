"""
Sets up sys.path and runs the app.

Use "python -i run.py" to start a console in the app environment.
"""
import os
import sys

sys.path.insert(1, os.path.join(os.path.abspath('.'), 'gaenv'))
import app #pylint: disable=W0611
