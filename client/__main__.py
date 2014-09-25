import os
import sys
sys.path.append(os.getcwd())
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from client.cli import ok

if __name__ == '__main__':
    ok.main()

