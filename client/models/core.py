import utils

class Test(object):
    """Represents all suites for a single test in an assignment."""

    def __init__(self, names=None, suites=None, points=0, setup=None,
            teardown=None, note='', cache=''):
        self.names = names or []
        # Filter out empty suites.
        if suites:
            self.suites = [suite for suite in suites if suite]
        else:
            self.suites = []
        self.points = points
        self.note = utils.dedent(note)
        self.cache = utils.dedent(cache)
        self.setup = setup or {}
        self.teardown = teardown or {}

    @property
    def name(self):
        """Gets the canonical name of this test.

        RETURNS:
        str; the name of the test
        """
        return self.names[0]

    @property
    def count_cases(self):
        return sum(len(suite) for suite in suites)

    @property
    def count_locked(self):
        return [case.is_locked for suite in suites
                               for case in suite].count(True)


class TestCase(object):
    """Represents a single test case."""

    def __init__(self, test, input_str, outputs, **status):
        # TODO(albert): validate that the number of prompts in 
        # lines is equal to the number of outputs
        # TODO(albert): scan lines for $; if no $ found, add one to
        # the last line.
        self._test = None      # The Test this case belongs to.
        self._input_str = utils.dedent(input_str)
        self._outputs = outputs
        self.status = status
        # TODO(albert): move this to subclass
        self.num_prompts = 0  # Number of prompts in self.lines.

    def on_grade(self):
        """Subclasses that are used by the grading protocol should
        implement this method.
        """
        # TODO(albert): more documentation
        pass

    def on_unlock(self):
        """Subclasses that are used by the unlocking protocol should
        implement this method.
        """
        pass

    @property
    def is_locked(self):
        return self.status.get('lock', True)

    def set_locked(self, locked):
        self.status['lock'] = locked

    @property
    def outputs(self):
        return self._outputs

    def set_outputs(self, new_outputs):
        self._outputs = new_outputs

    @property
    def lines(self):
        """Returns lines of code for the setup and actual test case."""
        # TODO(albert)

    @property
    def teardown(self):
        """Returns the teardown code for this particular TestCase."""
        # TODO(albert)


class TestCaseAnswer(object):
    """Represents an answer for a single TestCase."""

    def __init__(self, answer, choices=None, explanation=''):
        self.answer = answer
        self.choices = choices or []
        self.explanation = explanation

    @property
    def is_multiple_choice(self):
        return len(self.choices) > 0

