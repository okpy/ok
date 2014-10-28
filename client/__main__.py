import os
import sys
sys.path.append(os.getcwd())
# Add directory in which the ok.zip is stored to sys.path.
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

if sys.version_info[0] < 3:
	sys.exit("ok requires Python 3. \nFor more info: http://www-inst.eecs.berkeley.edu/~cs61a/fa14/lab/lab01/#installing-python")

from client.cli import ok

if __name__ == '__main__':
    ok.main()

