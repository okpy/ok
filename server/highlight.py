import os
import difflib
import itertools

import pygments
import pygments.lexers
import pygments.formatters

from server.constants import DIFF_SIZE_LIMIT, SOURCE_SIZE_LIMIT

class File:
    def __init__(self, name, lines=(), source='', too_big=False):
        self.lines = lines
        self.name = name.lower()
        self.too_big = too_big
        self.source = source
        _, self.extension = os.path.splitext(self.name)

class Line:
    def __init__(self, is_diff=True, tag=None,
                 line_before=None, line_after=None, contents='', comments=()):
        self.is_diff = is_diff
        self.tag = tag
        self.line_before = line_before
        self.line_after = line_after
        self.contents = contents
        self.comments = comments

def highlight(filename, source):
    """Highlights an input string into a list of HTML strings, one per line."""
    if not source:
        return []  # pygments does not play nice with empty files
    try:
        lexer = pygments.lexers.guess_lexer_for_filename(filename, source, stripnl=False)
    except pygments.util.ClassNotFound:
        lexer = pygments.lexers.TextLexer(stripnl=False)

    highlighted = pygments.highlight(source, lexer,
                                     pygments.formatters.HtmlFormatter(nowrap=True))
    return highlighted.splitlines(keepends=True)

def highlight_file(filename, source):
    """Given a source file, generate a sequence of (line index, HTML) pairs."""
    for i, contents in zip(itertools.count(1), highlight(filename, source)):
        yield Line(is_diff=False, tag='equal', line_after=i, contents=contents)

def highlight_diff(filename, a, b, diff_type='short'):
    """Given two input strings, generate a sequence of 4-tuples. The elements
    of each tuple are:
        * 'delete', 'insert', 'equal', or 'header' (the tag)
        * the line number of the first file (or None)
        * the line number of the second file (or None)
        * the rendered HTML string of the line

    DIFF_TYPE is either 'short' (3 lines of context) or
    'full' (all context lines).
    """
    highlighted_a = highlight(filename, a)
    highlighted_b = highlight(filename, b)

    def delete(i1, i2):
        for i in range(i1, i2):
            yield Line(
                tag='delete',
                line_before=i + 1,
                contents='-' + highlighted_a[i])

    def insert(i1, i2):
        for j in range(j1, j2):
            yield Line(
                tag='insert',
                line_after=j + 1,
                contents='+' + highlighted_b[j])

    def equal(i1, i2, j1, j2):
        for i, j in zip(range(i1, i2), range(j1, j2)):
            yield Line(
                tag='equal',
                line_before=i + 1,
                line_after=j + 1,
                contents=' ' + highlighted_b[j])

    def format_range_unified(start, stop):
        """Convert range to the "ed" format. From difflib.py"""
        # Per the diff spec at http://www.unix.org/single_unix_specification/
        beginning = start + 1     # lines start numbering with one
        length = stop - start
        if length == 1:
            return '{}'.format(beginning)
        if not length:
            beginning -= 1        # empty ranges begin at line just before the range
        return '{},{}'.format(beginning, length)

    matcher = difflib.SequenceMatcher(difflib.IS_CHARACTER_JUNK, a.splitlines(), b.splitlines())
    if diff_type == 'short':
        groups = matcher.get_grouped_opcodes()
    elif diff_type == 'full':
        opcodes = matcher.get_opcodes()
        if opcodes:
            groups = [opcodes]
        else:
            groups = []
    else:
        raise ValueError('Unknown diff type {}'.format(diff_type))
    for group in groups:
        first, last = group[0], group[-1]
        header = '@@ -{} +{} @@\n'.format(
            format_range_unified(first[1], last[2]),
            format_range_unified(first[3], last[4]))
        yield Line(tag='header', contents=header)
        for tag, i1, i2, j1, j2 in group:
            if tag == 'replace':
                yield from delete(i1, i2)
                yield from insert(j1, j2)
            elif tag == 'delete':
                yield from delete(i1, i2)
            elif tag == 'insert':
                yield from insert(j1, j2)
            elif tag == 'equal':
                yield from equal(i1, i2, j1, j2)

def highlight_range(filename, file, match_bundles, diff_type='short'):
    highlighted = highlight(filename, file)

    bundles = [x + 1 for x in sum(match_bundles, [])]
    # TODO: bundles.append(last line in file, if not already at the end)

    def get_next_pivot():
        return bundles.pop(0) if bundles else None

    # TESTING PORPOISES only:
    if filename == 'fizzbuzz.py':
        bundles = [1, 9, 10, 11]

    is_sim, line_number, next_pivot = False, 0, get_next_pivot()
    while bundles:
        if line_number == next_pivot:
            is_sim = not is_sim
            next_pivot = get_next_pivot()
        if is_sim:
            yield Line(tag='insert', line_after=line_number + 1,
                       contents='+' + highlighted[line_number])
        else:
            yield Line(tag='equal', line_after=line_number + 1,
                       contents=' ' + highlighted[line_number])
        line_number += 1

def sim_files(files_after, matches, diff_type='short'):
    # matches = {'fizzbuzz.py':    [[2, 9]],
    #            'moby_dick':      [],
    #            'notebook.ipynb': [[0, 203]]}

    # TODO: this is bad code. rewrite after it works.
    files = {}
    if diff_type:
        for filename in matches.keys():
            after = files_after.get(filename, '')
            if len(after) > DIFF_SIZE_LIMIT:
                files[filename] = File(filename, source=after, too_big=True)
            else:
                lines = list(highlight_range(filename, after, matches[filename], diff_type))
                files[filename] = File(filename, lines, after)
    else:
        for filename, source in files_after.items():
            if len(source) > SOURCE_SIZE_LIMIT:
                files[filename] = File(filename, too_big=True)
            else:
                lines = list(highlight_file(filename, source))
                files[filename] = File(filename, lines, source)
    return files

def diff_files(files_before, files_after, diff_type):
    files = {}
    if diff_type:
        for filename in files_before.keys() | files_after.keys():
            before = files_before.get(filename, '')
            after = files_after.get(filename, '')
            if len(before) > DIFF_SIZE_LIMIT or len(after) > DIFF_SIZE_LIMIT:
                files[filename] = File(filename, source=after, too_big=True)
            else:
                lines = list(highlight_diff(filename, before, after, diff_type))
                files[filename] = File(filename, lines, after)
    else:
        for filename, source in files_after.items():
            if len(source) > SOURCE_SIZE_LIMIT:
                files[filename] = File(filename, too_big=True)
            else:
                lines = list(highlight_file(filename, source))
                files[filename] = File(filename, lines, source)
    return files

def diff_lines(files_before, files_after):
    diff_lines = 0
    for filename in files_before.keys() | files_after.keys():
        a = files_before.get(filename, '')
        b = files_after.get(filename, '')
        matcher = difflib.SequenceMatcher(difflib.IS_CHARACTER_JUNK, a.splitlines(), b.splitlines())
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                diff_lines += (j2 - j1) + (i2 - i1)
            elif tag == 'delete':
                diff_lines += (i2 - i1)
            elif tag == 'insert':
                diff_lines += (j2 - j1)
    return diff_lines

def lines_added(files_before, files_after):
    added = 0
    for filename in files_before.keys() | files_after.keys():
        a = files_before.get(filename, '')
        b = files_after.get(filename, '')
        matcher = difflib.SequenceMatcher(difflib.IS_CHARACTER_JUNK, a.splitlines(), b.splitlines())
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                added += (j2 - j1)
            elif tag == 'insert':
                added += (j2 - j1)
    return added
