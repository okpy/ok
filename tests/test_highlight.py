import itertools
import jinja2
import os
import re
import tempfile
import subprocess

from server import highlight

from tests import OkTestCase

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
            'before.py': open('tests/files/difflib_before.py').read(),
            'after.py': open('tests/files/difflib_after.py').read()
        }

    def _test_highlight_file(self, filename, source):
        source_lines = source.splitlines(keepends=True)
        highlighted = list(highlight.highlight_file(filename, source))

        # Check format
        for line in highlighted:
            assert source_lines[line.line_after - 1] == striptags(line.contents)

        # Check that removing tags gives the same file
        assert source_lines == [striptags(line.contents) for line in highlighted]

    def _test_highlight_diff(self, filename, a, b, diff_type):
        a_lines = a.splitlines(keepends=True)
        b_lines = b.splitlines(keepends=True)
        highlighted = list(highlight.highlight_diff(filename, a, b, diff_type))

        # Check format
        for line in highlighted:
            stripped = striptags(line.contents)
            start = stripped[0]
            source = stripped[1:]
            if line.tag == 'header':
                assert line.line_before is None
                assert line.line_after is None
            elif line.tag == 'delete':
                assert start == '-'
                assert a_lines[line.line_before - 1] == source
                assert line.line_after is None
            elif line.tag == 'insert':
                assert start == '+'
                assert line.line_before is None
                assert b_lines[line.line_after - 1] == source
            elif line.tag == 'equal':
                assert start == ' '
                assert a_lines[line.line_before - 1] == source
                assert b_lines[line.line_after - 1] == source
            else:
                raise AssertionError('Unknown tag {}'.format(tag))

        # Check that removing tags gives a patch that can be applied
        patch = ''.join(striptags(line.contents) for line in highlighted)
        assert b_lines == apply_patch(patch, a).splitlines(keepends=True)

    def test_highlight_file(self):
        for filename, source in self.files.items():
            self._test_highlight_file(filename, source)

    def test_highlight_diff(self):
        for diff_type in ('short', 'full'):
            for a, b in itertools.combinations(self.files.values(), 2):
                self._test_highlight_diff('test.py', a, b, diff_type)

    def test_no_highlight(self):
        filename = 'data'
        source = 'It was the best of times, it was the worst of times, ...'

        source_lines = source.splitlines(keepends=True)
        highlighted = list(highlight.highlight_file(filename, source))

        for line in highlighted:
            assert source_lines[line.line_after - 1] == striptags(line.contents)

        assert source_lines == [line.contents for line in highlighted]
