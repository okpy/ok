"""Core test models.

Ok.py assignments are organized in the following hierarchy:

    * assignments: consist of a list of Test objects
    * Test: consist of a list of suites
    * suite: a list of TestCase objects
    * TestCase (and its subclasses): consist of
        * an input
        * a list of TestCaseAnswers
    * TestCaseAnswers: represents the answer to a specific TestCase

The core models (Test, TestCase, TestCaseAnswers) are implemented
here.

Developers can extend the TestCase class to create different types of
TestCases (both interfaces and concrete subclasses of TestCase are
encouraged). TestCase interfaces should be located with their
respective Protocols (in the client/protocols/ directory), while
concrete subclasses of TestCase should be located in client/models/.
"""

import utils

class Test(object):
    """Represents all suites for a single test in an assignment."""

    def __init__(self, names=None, suites=None, points=0, note='', cache=''):
        self.names = names or []
        # Filter out empty suites.
        suites = suites or []
        self.suites = list(filter(lambda suite: suite != [], suites))

        self.points = points
        self.note = utils.dedent(note)
        # TODO(albert): the notion of a cache was originally designed
        # only for code-based questions. Either generalize for other
        # test types, or move to subclasses.
        self.cache = utils.dedent(cache)

    @property
    def name(self):
        """Gets the canonical name of this test.

        RETURNS:
        str; the name of the test
        """
        if not self.names:
            return repr(self)
        return self.names[0]

    @property
    def count_cases(self):
        """Returns the number of test cases in this test."""
        return sum(len(suite) for suite in self.suites)

    @property
    def count_locked(self):
        """Returns the number of locked test cases in this test."""
        return [case.is_locked for suite in self.suites
                               for case in suite].count(True)

    def add_suite(self, suite):
        """Adds the given suite to this test's list of suites. If
        suite is empty, do nothing."""
        if suite:
            self.suites.append(suite)
            suite_num = len(self.suites) - 1
            for test_case in suite:
                test_case.test = self
                test_case.suite_num = suite_num

    @classmethod
    def serialize(cls, test_json, assignment_info):
        """Serializes a JSON object into a Test object, given a
        particular set of assignment_info.

        PARAMETERS:
        test_json       -- JSON; the JSON representation of the test.
        assignment_info -- JSON; information about the assignment,
                           may be used by TestCases.

        RETURNS:
        Test
        """
        # TODO(albert): implement stub.
        pass

    def deserialize(self):
        """Deserializes this Test object into JSON format.

        RETURNS:
        JSON as a plain-old-Python-object.
        """
        # TODO(albert): implement stub.
        pass

class TestCase(object):
    """Represents a single test case."""

    def __init__(self, input_str, outputs, test=None, **status):
        """Constructor.

        PARAMETERS:
        input_str -- str; the TestCase's input.
        outputs   -- list of TestCaseAnswers; the outputs associated
                     with this TestCase.
        test      -- Test; the test to which this TestCase belongs.
        status    -- keyword arguments; the status of this TestCase.
        """
        self._input_str = utils.dedent(input_str)
        self._outputs = outputs
        self.test = test
        self._status = status

    @property
    def is_locked(self):
        """Returns True if the TestCase is locked."""
        return self._status.get('lock', True)

    def set_locked(self, locked):
        """Sets the TestCase's locked status."""
        self._status['lock'] = locked

    @property
    def outputs(self):
        """Returns a list of TestCaseAnswers associated with this
        TestCase.
        """
        return self._outputs

    def set_outputs(self, new_outputs):
        """Sets this TestCase's list of TestCaseAnswers."""
        self._outputs = new_outputs

    @property
    def type(self):
        """Subclasses should implement a type tag."""
        return 'default'

class TestCaseAnswer(object):
    """Represents an answer for a single TestCase."""

    def __init__(self, answer, choices=None, explanation=''):
        """Constructor.

        PARAMETERS:
        answer      -- str; The correct answer, possibly encoded.
        choices     -- list of strs; If not None, denotes a list of
                       options for multiple choice.
        explanation -- str; Optional explanation of the TestCaseAnswer.
        """
        self.answer = answer
        self.choices = choices or []
        self.explanation = explanation

    @property
    def is_multiple_choice(self):
        """Returns True if the TestCaseAnswer is multiple choice."""
        return len(self.choices) > 0

