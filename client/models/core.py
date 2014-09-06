"""Core test models.

Ok.py assignments are organized in the following hierarchy:

    * assignments: consist of a list of Test objects
    * Test: consist of a list of suites
    * suite: a list of TestCase objects
    * TestCase (and its subclasses)

The core models (Assignment, Test, TestCase) are implemented here.

Developers can extend the TestCase class to create different types of
TestCases (both interfaces and concrete subclasses of TestCase are
encouraged). TestCase interfaces should be located with their
respective Protocols (in the client/protocols/ directory), while
concrete subclasses of TestCase should be located in client/models/.
"""

from models import serialize
import exceptions
import utils

class Assignment(serialize.Serializable):
    """A representation of an assignment."""

    REQUIRED = {
        'name': serialize.STR,
        'version': serialize.STR,
    }
    OPTIONAL = {
        'src_files': serialize.LIST,
        'params': serialize.DICT,
        'hash_key': serialize.STR,
    }

    def __init__(self, **fields):
        super().__init__(**fields)
        self._tests = []

    def add_test(self, test):
        assert isinstance(test, Test), '{} must be a Test'.format(test)
        self._tests.append(test)

    @property
    def tests(self):
        """Returns the tests for this assignment. The returned list
        is a copy, so that the original list can remain immutable.
        """
        return self._tests[:]

    @property
    def num_tests(self):
        return len(self._tests)

class Test(serialize.Serializable):
    """Represents all suites for a single test in an assignment."""

    REQUIRED = {
        'names': serialize.SerializeArray(serialize.STR),
        'points': serialize.FLOAT,
    }
    OPTIONAL = {
        'suites': serialize.SerializeArray(serialize.LIST),
        'params': serialize.DICT,
        'note': serialize.STR,
        'extra': serialize.BOOL_FALSE,
    }

    @property
    def name(self):
        """Gets the canonical name of this test.

        RETURNS:
        str; the name of the test
        """
        if not self['names']:
            return repr(self)
        return self['names'][0]

    @property
    def num_cases(self):
        """Returns the number of test cases in this test."""
        return sum(len(suite) for suite in self['suites'])

    @property
    def num_locked(self):
        """Returns the number of locked test cases in this test."""
        return [case['locked'] for suite in self['suites']
                               for case in suite].count(True)

    @property
    def num_graded(self):
        return [case.should_grade() for suite in self['suites']
                                    for case in suite].count(True)

    def add_suite(self, suite):
        """Adds the given suite to this test's list of suites. If
        suite is empty, do nothing."""
        if suite:
            self['suites'].append(suite)

    @classmethod
    def deserialize(cls, test_json, assignment, case_map):
        """Deserializes a JSON object into a Test object, given a
        particular set of assignment_info.

        PARAMETERS:
        test_json  -- JSON; the JSON representation of the test.
        assignment -- Assignment; information about the assignment,
                      may be used by TestCases.
        case_map   -- dict; maps case tags (strings) to TestCase
                      classes.

        RETURNS:
        Test
        """
        test = Test(**test_json)
        new_suites = []
        for suite in test['suites']:
            if not suite:
                continue
            new_suite = []
            for case_json in suite:
                if 'type' not in case_json:
                    raise exceptions.DeserializeError.missing_fields(('type'))
                case_type = case_json['type']
                if case_type not in case_map:
                    raise exceptions.DeserializeError.unknown_type(
                            case_type, case_map)
                test_case = case_map[case_type].deserialize(
                        case_json, assignment, test)
                new_suite.append(test_case)
            new_suites.append(new_suite)
        test['suites'] = new_suites
        return test

    def serialize(self):
        """Serializes this Test object into JSON format.

        RETURNS:
        JSON as a plain-old-Python-object.
        """
        json = super().serialize()
        suites = [[case.serialize() for case in suite]
                                    for suite in self['suites']]
        if suites:
            json['suites'] = suites
        return json

class TestCase(serialize.Serializable):
    """Represents a single test case."""

    type = 'default'

    REQUIRED = {
        'type': serialize.STR,
    }

    @classmethod
    def deserialize(cls, json, assignment, test):
        result = super().deserialize(json)
        result._assertType()
        return result

    def _assertType(self):
        if self['type'] != self.type:
            raise exceptions.DeserializeError.unexpected_value('type',
                    self.type, self['type'])

