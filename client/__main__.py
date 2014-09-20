import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.getcwd())

from client import ok

def main():
    ok.ok_main(ok.parse_input())

if __name__ == '__main__':
    main()

