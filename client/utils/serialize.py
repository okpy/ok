from exceptions import serialize

class Serializable(object):
    """An abstract class for serializable objects."""

    # Subclasses should override these variables with required and
    # optional fields.
    REQUIRED = dict()
    OPTIONAL = dict()

    def __init__(self, **fields):
        self._fields = {}
        for field, value in fields.items():
            self._validate(field, value)
            self._fields[field] = value

        # Error if any required fields are missing.
        missing_fields = set(self.REQUIRED) - set(self._fields)
        if missing_fields:
            raise serialize.DeserializeError.missing_fields(
                    missing_fields)

        # Set defaults for missing optional fields.
        for field in set(self.OPTIONAL) - set(self._fields):
            self._fields[field] = self.OPTIONAL[field].default

    #############
    # Interface #
    #############

    @classmethod
    def deserialize(cls, fields):
        """Creates an instance of this Serialiable object, with the
        given fields. Subclasses can override this method to change
        deserialization behavior.
        """
        return cls(**json)

    def serialize(self):
        """Serializes this object into JSON format. The default
        behavior simply returns a copy a of all the fields.
        """
        return self._fields.copy()

    #############################
    # Getitem/Setitem interface #
    #############################

    def __getitem__(self, field):
        if field not in self._fields:
            raise KeyError(field)
        return self._fields[field]

    def __setitem__(self, field, value):
        """Sets the given field to the given value, if the value is
        valid for the field.
        """
        self._validate(field, value)
        self._fields[field] = value

    ###################
    # Private Methods #
    ###################

    def _field_type(self, field):
        """Returns the SerializeType of the field. If the field is
        unexpected, an AttributeError is thrown.
        """
        if field in self.REQUIRED:
            return self.REQUIRED[field]
        elif field in self.OPTIONAL:
            return self.OPTIONAL[field]
        raise AttributeError('{} has no field {}'.format(
            self.__class__.__name__, field))

    def _validate(self, field, value):
        """Checks that a value is the correct type for a given field.
        It is an error if the field is unexpected.
        """
        try:
            field_type = self._field_type(field)
        except AttributeError:
            raise serialize.DeserializeError.unexpected_field()
        if not field_type.validate(value):
            raise serialize.DeserializeError.unexpected_type(
                    field, field_type, value)


######################
# Serializable Types #
######################

class SerializePrimitive(object):
    def __init__(self, default, *valid_types):
        self._default = default
        assert len(valid_types) > 0, 'Needs at least one valid type'
        self._valid_types = valid_types

    @property
    def default(self):
        return self._default

    def validate(self, obj):
        return type(obj) in self._valid_types

    def __str__(self):
        return self._valid_types[0].__name__


class SerializeType(object):
    """A serializable type."""
    def __init__(self, type, *args):
        self._type = type
        self._args = args

    @property
    def default(self):
        return self._type(*self._args)

    def validate(self, obj):
        return type(obj) == self._type

    def __str__(self):
        return self._type.__name__


BOOL = SerializePrimitive(False, bool)
INT = SerializePrimitive(0, int)
FLOAT = SerializePrimitive(0, float, int)
STR = SerializePrimitive('', str)
DICT = SerializeType(dict)
LIST = SerializeType(list)
