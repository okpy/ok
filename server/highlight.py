import difflib

import pygments
import pygments.lexers
import pygments.formatters

def highlight(filename, source):
    """Highlights an input string into an HTML string."""
    return pygments.highlight(source,
        pygments.lexers.guess_lexer_for_filename(filename, source, stripnl=False),
        pygments.formatters.HtmlFormatter(nowrap=True))

def highlight_diff(filename, a, b):
    """Given two input strings, generate a sequence of 4-tuples. The elements
    of each tuple are:
        * 'delete', 'insert', or 'equal' (the tag)
        * the line number of the first file (or None)
        * the line number of the second file (or None)
        * the rendered HTML string of the line
    """
    highlighted_a = highlight(filename, a).splitlines()
    highlighted_b = highlight(filename, b).splitlines()
    matcher = difflib.SequenceMatcher(None, a.splitlines(), b.splitlines())
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'replace':
            for i in range(i1, i2):
                yield 'delete', i, None, highlighted_a[i]
            for j in range(j1, j2):
                yield 'insert', None, j, highlighted_b[j]
        elif tag == 'delete':
            for i in range(i1, i2):
                yield 'delete', i, None, highlighted_a[i]
        elif tag == 'insert':
            for j in range(j1, j2):
                yield 'insert', None, j, highlighted_b[j]
        elif tag == 'equal':
            for i, j in zip(range(i1, i2), range(j1, j2)):
                yield 'equal', i, j, highlighted_b[j]
