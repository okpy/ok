import difflib

differ = difflib.Differ()

def diff(s1, s2):
    lines1 = s1.split('\n')
    lines2 = s2.split('\n')
    return list(differ.compare(lines1, lines2))