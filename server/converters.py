from werkzeug.routing import BaseConverter, ValidationError

from server import constants, utils

class BoolConverter(BaseConverter):
    def __init__(self, url_map, false_value, true_value):
        super(BoolConverter, self).__init__(url_map)
        self.false_value = false_value
        self.true_value = true_value
        self.regex = '(?:{0}|{1})'.format(false_value, true_value)

    def to_python(self, value):
        return value == self.true_value

    def to_url(self, value):
        return self.true_value if value else self.false_value

class HashidConverter(BaseConverter):
    def to_python(self, value):
        try:
            return utils.decode_id(value)
        except TypeError as e:
            raise ValidationError(str(e))

    def to_url(self, value):
        return utils.encode_id(value)

name_part = '[^/]+'

def restricted_name_part(exceptions):
    """Return a regex that matches a URL part except one of the words in the
    exceptions list.
    """
    # (?!...) is a negative lookahead
    return ''.join('(?!{}/)'.format(w) for w in exceptions) + name_part

class OfferingConverter(BaseConverter):
    regex = restricted_name_part(constants.FORBIDDEN_ROUTE_NAMES) + \
        '/' + name_part + '/' + name_part

class AssignmentNameConverter(BaseConverter):
    regex = OfferingConverter.regex + '/' + \
        restricted_name_part(constants.FORBIDDEN_ASSIGNMENT_NAMES)

def init_app(app):
    app.url_map.converters['bool'] = BoolConverter
    app.url_map.converters['hashid'] = HashidConverter
    app.url_map.converters['offering'] = OfferingConverter
    app.url_map.converters['assignment_name'] = AssignmentNameConverter
