~ name: tuple-replace ~
~ topics: tuples, hofs ~
~ type: coding ~
~ language: python ~

~ question ~
Define tuple_replace, which takes a tuple TUP and a number N, and returns a function with input function FN that replaces the elements N to len(TUP) - 1 with those same elements, now applied with FN. If N does not exist in the tuple, return the tuple unchanged.

~ template ~
def tuple_replace(tup, n):
    '''
    >>> orig_tup = (2,4,6,8)
    >>> add_four = lambda x : x + 4
    >>> tuple_replace(orig_tup, 2)(add_four)
    (2, 4, 10, 12)
    >>> tuple_replace(orig_tup, 5)(lambda x : x * x)
    (2, 4, 6, 8)
    '''
    ## YOUR CODE HERE ##

~ solution ~
def tuple_replace(tup, n):
    def gen(fn):
        count, result, apply = 0, (), False
        while count < len(tup):
            if count == n:
                apply = True
            if apply:
                result += (fn(tup[count]),)
            else:
                result += (tup[count],)
            count += 1
        return result
    return gen