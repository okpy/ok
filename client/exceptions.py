class OkException(BaseException):
    """Base exception for ok.py."""
    pass

class DeserializeError(OkException):

    @classmethod
    def expect_dict(cls, json):
        return DeserializeError('Expected JSON dict, got {}'.format(
            type(json).__name__))

    @classmethod
    def expect_list(cls, json):
        return DeserializeError('Expected JSON list, got {}'.format(
            type(json).__name__))

    @classmethod
    def missing_fields(cls, fields):
        return DeserializeError('Missing fields: {}'.format(
            ', '.join(fields)))

    @classmethod
    def unexpected_field(cls, field):
        return DeserializeError('Unexpected field: {}'.format(field))

    @classmethod
    def unexpected_value(cls, field, expect, actual):
        return DeserializeError(
            'Field "{}" expected value {}, got {}'.format(field, expect, actual))

    @classmethod
    def unexpected_type(cls, field, expect, actual):
        return DeserializeError(
            'Field "{}" expected type {}, got {}'.format(field, expect, repr(actual)))

    @classmethod
    def unknown_type(cls, type, case_map):
        return DeserializeError(
            'TestCase type "{}" is unknown in case map {}'.format(type,
                case_map))

