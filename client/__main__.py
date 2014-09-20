import sys
sys.path.append('.')

# List of unsupported in (Major, Minor, Micro) form. 
# unsupported_versions = [(1,2,2)]

# Basic Version Checking
if sys.version_info[0] < 3:
	sys.exit("ok requires Python 3. \nFor more info: http://www-inst.eecs.berkeley.edu/~cs61a/fa14/lab/lab01/#installing-python")

# TODO: List of unsupported in (Major, Minor, Micro) form. 
# unsupported_versions = [(1,2,2)]

def main():
	import ok
	args = ok.parse_input()
	if not args.local:
		try:
			import ssl
		except: 
			sys.exit("SSL Bindings are not installed. Try to enable python3 ssl support. \nPlease try another OS or contact staff")
	ok.ok_main(args)

if __name__ == '__main__':
    main()
