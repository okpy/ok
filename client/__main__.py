import sys
sys.path.append('.')

# List of unsupported in (Major, Minor, Micro) form. 
# unsupported_versions = [(1,2,2)]

# Basic Version Checking
if sys.version_info[0] < 3:
	sys.exit("ok requires Python 3. \nFor more info: http://www-inst.eecs.berkeley.edu/~cs61a/fa14/lab/lab01/#installing-python")

try: 
	import ssl
except Exception as e:
	print(e)
	sys.exit("Please run ok with the --local flag \n i.e. python3 ok -u --local")

import ok
def main():
    ok.ok_main(ok.parse_input())

if __name__ == '__main__':
    main()

