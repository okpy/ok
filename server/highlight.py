import difflib
import itertools

import pygments
import pygments.lexers
import pygments.formatters

def highlight(filename, source):
    """Highlights an input string into an HTML string."""
    return pygments.highlight(source,
        pygments.lexers.guess_lexer_for_filename(filename, source, stripnl=False),
        pygments.formatters.HtmlFormatter(nowrap=True))

def highlight_file(filename, source):
    """Given a source file, generate a sequence of (line index, HTML) pairs."""
    return zip(itertools.count(1), highlight(filename, source).splitlines())

def highlight_diff(filename, a, b):
    """Given two input strings, generate a sequence of 4-tuples. The elements
    of each tuple are:
        * 'delete', 'insert', 'equal', or 'header' (the tag)
        * the line number of the first file (or None)
        * the line number of the second file (or None)
        * the rendered HTML string of the line
    """
    highlighted_a = highlight(filename, a).splitlines()
    highlighted_b = highlight(filename, b).splitlines()

    def delete(i1, i2):
        for i in range(i1, i2):
            yield 'delete', i + 1, None, '-' + highlighted_a[i]

    def insert(i1, i2):
        for j in range(j1, j2):
            yield 'insert', None, j + 1, '+' + highlighted_b[j]

    def equal(i1, i2, j1, j2):
        for i, j in zip(range(i1, i2), range(j1, j2)):
            yield 'equal', i + 1, j + 1, ' ' + highlighted_b[j]

    matcher = difflib.SequenceMatcher(None, a.splitlines(), b.splitlines())
    for group in matcher.get_grouped_opcodes():
        first, last = group[0], group[-1]
        header = '@@ -{},{} +{},{} @@'.format(first[1], last[2], first[3], last[4])
        yield 'header', None, None, header
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
