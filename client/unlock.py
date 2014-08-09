#######################
# UNLOCKING MECHANISM #
#######################

def __make_hash_fn(hash_key, encoding='utf-8'):
    def hash_fn(x):
        return hmac.new(hash_key.encode(encoding),
                        x.encode(encoding)).digest()
    return hash_fn

hash_key = tests['project_info']['hash_key']
__make_hash_fn(hash_key)

def unlock(test, hash_fn):
    """Unlocks TestCases for a given Test.

    PARAMETERS:
    test -- Test; the test to unlock.

    DESCRIPTION:
    This function incrementally unlocks all TestCases in a specified
    Test. Students must answer in the order that TestCases are
    written. Once a TestCase is unlocked, it will remain unlocked.

    Persistant state is stored by rewriting the contents of
    tests.pkl. Students should NOT manually change these files.
    """
    name = test.name

    if not test.suites:
        print('No tests to unlock for {}.'.format(name))
        return

    prompt = '?'
    underline('Unlocking tests for {}'.format(name))
    print('At each "{}", type in what you would expect the output to '
          'be if you had implemented {}'.format(prompt, name))
    print('Type exit() to quit')
    print()

    cases = 0
    for suite_num, suite in enumerate(test.suites):
        for case_num, case in enumerate(suite):
            if not case.is_conceptual:
                # TODO(albert): what is this for?
                cases += 1
            if not case.is_locked:
                continue
            underline('Case {}'.format(cases), under='-')
            if case.is_conceptual:
                __unlock_concept(case)
                continue
            else:
                __unlock_code(case)
    print("You are done unlocking tests for this question!")

def __unlock_code(case, hash_fn):
    num_prompts = case.num_prompts
    lines = case.lines
    outputs = iter(case.outputs)
    answers = []
    for line in lines:
        if len(lines) > 1 and not line.startswith('$'):
            if line.startswith(' '): # indented
                print(PS2 + line)
            else:
                print(PS1 + line)
            continue
        line = line.replace('$ ', '')
        print(PS1 + line)
        answer = handle_student_input(next(outputs), prompt, hash_fn)
        if answer is None:
            return
        answers.append(answer)
    case[1] = answers
    case[2] += 'unlock'
    print("-- Congratulations, you have unlocked this case! --")
    print()

def __unlock_concept(case, hash_fn):
    underline('Concept Question', under='-')
    print(split(case[0], join_str='\n'))
    answer = handle_student_input(case[1][0], prompt, hash_fn)
    if answer is None:
        return
    case[1] = [answer]
    case[2] += 'unlock'
    print("-- Congratulations, you have unlocked this case! --")
    print()

def handle_student_input(output, prompt, hash_fn):
    """Reads student input for unlocking tests.

    PARAMETERS:
    output  -- str or tuple; if str, represents the hashed version of
               the correct output. If tuple, represents a sequence of
               choices (strings) from which the student can choose
    prompt  -- str; the prompt to display when asking for student input
    hash_fn -- function; hash function

    DESCRIPTION:
    Continually prompt the student for an answer to an unlocking
    question until one of the folliwng happens:

        `1. The student supplies the correct answer, in which case
            the supplied answer is returned
         2. The student aborts abnormally (either by typing 'exit()' or
            using Ctrl-C/D. In this case, return None

    Correctness is determined by hashing student input and comparing
    to the parameter "output", which is a hashed version of the correct
    answer. If the hashes are equal, the student answer is assumed to
    be correct.

    RETURNS:
    str  -- the correct solution (that the student supplied)
    None -- indicates an abnormal exit from input prompt
    """
    answer = output
    correct = False
    while not correct:
        if type(output) == tuple:
            print()
            print("Choose the number of the correct choice:")
            for i, choice in enumerate(random.sample(output, len(output))):
                print('    ' + str(i) + ') ' + split(choice, join_str='\n       '))
                if choice == output[0]:
                    answer = hash_fn(str(i))
        sys.stdout = sys.__stdout__
        try:
            student_input = input(prompt + ' ')
        except (KeyboardInterrupt, EOFError):
            try:
                print('\nExiting unlocker...')
            # When you use Ctrl+C in Windows, it throws
            # two exceptions, so you need to catch both of
            # them.... aka Windows is terrible.
            except (KeyboardInterrupt, EOFError):
                pass
            return
        finally:
            sys.stdout = logger
        if student_input in ('exit()', 'quit()'):
            print('\nExiting unlocker...')
            return
        correct = hash_fn(student_input) == answer
        if not correct:
            print("-- Not quite. Try again! --")
    if type(output) == tuple:
        student_input = output[0]
    return student_input
