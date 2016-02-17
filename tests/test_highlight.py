import itertools
import jinja2
import os
import re
import tempfile
import subprocess

from server import highlight

from .helpers import OkTestCase

_striptags_re = re.compile(r'(<!--.*?-->|<[^>]*>)')

def striptags(s):
    stripped = _striptags_re.sub('', s)
    return jinja2.Markup(stripped).unescape()

def apply_patch(patch, source):
    """Applies a patch to a source string, returning the result string."""
    with tempfile.NamedTemporaryFile('w+') as infile:
        with tempfile.NamedTemporaryFile('r') as outfile:
            infile.write(source)
            proc = subprocess.Popen(['patch', '-p0', '-o', outfile.name, infile.name],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True)
            outs, errs = proc.communicate(input=patch)
            if proc.returncode != 0:
                raise AssertionError('patch failed: {}'.format(errs))
            return outfile.read()

class TestHighlight(OkTestCase):
    def setUp(self):
        super(TestHighlight, self).setUp()
        self.files = {
            'before.py': open('tests/files/before.py').read(),
            'after.py': open('tests/files/after.py').read()
        }

    def _test_highlight_file(self, filename, source):
        source_lines = source.splitlines(keepends=True)
        highlighted = list(highlight.highlight_file(filename, source))

        # Check format
        for i, highlighted_line in highlighted:
            assert source_lines[i - 1] == striptags(highlighted_line)

        # Check that removing tags gives the same file
        assert source_lines == [striptags(line) for _, line in highlighted]

    def _test_highlight_diff(self, filename, a, b):
        a_lines = a.splitlines(keepends=True)
        b_lines = b.splitlines(keepends=True)
        highlighted = list(highlight.highlight_diff(filename, a, b))

        # Check format
        for tag, i, j, highlighted_line in highlighted:
            stripped = striptags(highlighted_line)
            start = stripped[0]
            line = stripped[1:]
            if tag == 'header':
                assert i is None
                assert j is None
            elif tag == 'delete':
                assert start == '-'
                assert a_lines[i - 1] == line
                assert j is None
            elif tag == 'insert':
                assert start == '+'
                assert i is None
                assert b_lines[j - 1] == line
            elif tag == 'equal':
                assert start == ' '
                assert a_lines[i - 1] == line
                assert b_lines[j - 1] == line
            else:
                raise AssertionError('Unknown tag {}'.format(tag))

        # Check that removing tags gives a patch that can be applied
        patch = ''.join(striptags(line) for _, _, _, line in highlighted)
        assert b_lines == apply_patch(patch, a).splitlines(keepends=True)

    def test_highlight_file(self):
        for filename, source in self.files.items():
            self._test_highlight_file(filename, source)

    def test_highlight_diff(self):
        for a, b in itertools.combinations(self.files.values(), 2):
            self._test_highlight_diff('test.py', a, b)
