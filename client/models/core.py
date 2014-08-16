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
        self._test = test  # The Test this case belongs to.
        self._input_str = utils.dedent(input_str)
        self._outputs = outputs
        self._status = status

    def on_grade(self, logger, verbose, interact):
        """Subclasses that are used by the grading protocol should
        implement this method.
        """
        # TODO(albert): more documentation
        pass

    def on_unlock(self, logger):
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
    def type(self):
        """Subclasses should implement a type tag."""
        return 'default'


class TestCaseAnswer(object):
    """Represents an answer for a single TestCase."""

    def __init__(self, answer, choices=None, explanation=''):
        self.answer = answer
        self.choices = choices or []
        self.explanation = explanation

    @property
    def is_multiple_choice(self):
        return len(self.choices) > 0

