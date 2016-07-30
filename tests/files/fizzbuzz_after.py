# Sample long line. Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum
def fizz_buzz(n):
    for num in range(1, n + 1):
        msg = ''
        if num % 3 == 0:
            msg += 'Fizz🍪'
        if num % 5 == 0:
            msg += 'Buzz'
        print(msg or num)

if __name__ == '__main__':
    fizz_buzz(100)
