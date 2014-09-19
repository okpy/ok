"""Client exceptions."""

class OkException(BaseException):
    """Base exception for ok.py."""
    pass

# TODO(albert): extend from a base class designed for student bugs.
class Timeout(BaseException):
    """Exception for timeouts."""
    _message = 'Evaluation timed out!'

    def __init__(self, timeout):
        """Constructor.

        PARAMTERS:
        timeout -- int; number of seconds before timeout error occurred
        """
        super().__init__(self)
        self.timeout = timeout


class DeserializeError(OkException):
    """Exceptions related to deserialization."""

    @classmethod
    def expect_dict(cls, json):
        return cls('Expected JSON dict, got {}'.format(
            type(json).__name__))

    @classmethod
    def expect_list(cls, json):
        return cls('Expected JSON list, got {}'.format(
            type(json).__name__))

    @classmethod
    def missing_fields(cls, fields):
        return cls('Missing fields: {}'.format(
            ', '.join(fields)))

    @classmethod
    def unexpected_field(cls, field):
        return cls('Unexpected field: {}'.format(field))

    @classmethod
    def unexpected_value(cls, field, expect, actual):
        return cls(
            'Field "{}" expected value {}, got {}'.format(
                field, expect, actual))

    @classmethod
    def unexpected_type(cls, field, expect, actual):
        return cls(
            'Field "{}" expected type {}, got {}'.format(
                field, expect, repr(actual)))

    @classmethod
    def unknown_type(cls, type_, case_map):
        return cls(
            'TestCase type "{}" is unknown in case map {}'.format(
                type_, case_map))

