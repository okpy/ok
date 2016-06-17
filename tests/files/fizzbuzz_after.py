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
