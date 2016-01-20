import difflib

def generate_diff(before, after):
    """Return a dictionary of diff objects."""
    differ = difflib.ndiff
    if before is None:
        before = {}
    diffs = {}
    for file in after:
        if file == 'submit':
            continue
        file_before = before.get(file, '').split('\n')
        file_after = after[file].split('\n')
        file_diff = differ(file_before, file_after)
        diffs[file] = DiffFileView(file_diff)
    return diffs

class DiffFileView(object):
    def __init__(self, diff):
        self.diff = diff
        self.lines = []
        self._process()

    def _process(self):
        left_line_no = 0
        right_line_no = 0
        for line in self.diff:
            sign = line[0]
            line = line[2:]
            left = right = ''
            if sign == '+':
                right_line_no += 1
                right = right_line_no
            elif sign == '-':
                left_line_no += 1
                left = left_line_no
            elif sign == '?':
                # TODO: add in-line diff by modifying last line in list
                # print(self.lines[-1][-1])
                # print(line)
                continue
            else:
                left_line_no += 1
                right_line_no += 1
                left, right = left_line_no, right_line_no
            if sign == '-':
                cls = 'diff-before'
            elif sign == '+':
                cls = 'diff-after'
            else:
                cls = 'diff-none'
            self.lines.append((cls, left, right, line))
