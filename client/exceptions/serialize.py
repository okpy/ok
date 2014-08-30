from exceptions import core

class DeserializeError(core.OkException):

    @classmethod
    def expect_dict(self, json):
        return DeserializeError('Expected JSON dict, got {}'.format(
            type(json).__name__))

    @classmethod
    def expect_list(self, json):
        return DeserializeError('Expected JSON list, got {}'.format(
            type(json).__name__))

    @classmethod
    def missing_fields(self, fields):
        return DeserializeError('Missing fields: {}'.format(
            ', '.join(fields)))

    @classmethod
    def unexpected_field(self, field):
        return DeserializeError('Unexpected field: {}'.format(field))

    @classmethod
    def unexpected_value(self, field, expect, actual):
        return DeserializeError(
            'Field "{}" expected value {}, got {}'.format(field, expect, actual))

    @classmethod
    def unexpected_type(self, field, expect, actual):
        return DeserializeError(
            'Field "{}" expected type {}, got {}'.format(field, expect, actual))
