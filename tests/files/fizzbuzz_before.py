if __name__ == '__main__':
    for num in range(1, 101):
        msg = ''
        if num % 3 == 0:
            msg += 'Fizz'
        if num % 5 == 0:
            msg += 'Buzz'
        print(msg or num)
