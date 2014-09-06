import exceptions

class Serializable(object):
    """An abstract class for serializable objects."""

    # Subclasses should override these variables with required and
    # optional fields.
    REQUIRED = dict()
    OPTIONAL = dict()
    # TODO(albert): right now, subclasses must explicitly list
    # the superclass's REQUIRED and OPTIONAL fields, since multiple
    # intheritance makes attribute lookup complicated.

    def __init__(self, **fields):
        self._fields = {}
        for field, value in fields.items():
            self._validate(field, value)
            self._fields[field] = value

        # Error if any required fields are missing.
        missing_fields = set(self.REQUIRED) - set(self._fields)
        if missing_fields:
            raise exceptions.DeserializeError.missing_fields(
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
        return cls(**fields)

    def serialize(self):
        """Serializes this object into JSON format. The default
        behavior simply returns a copy a of all the fields.
        """
        json = {}
        for field, value in self._fields.items():
            if value != self._field_type(field).default or field in self.REQUIRED:
                json[field] = value
        return json

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
            raise exceptions.DeserializeError.unexpected_field(field)
        if not field_type.validate(value):
            raise exceptions.DeserializeError.unexpected_type(
                    field, field_type, value)

######################
# Serializable Types #
######################

class SerializeType(object):
    """An interface for serializable types."""
    @property
    def default(self):
        raise NotImplementedError

    def validate(self, obj):
        raise NotImplementedError

class SerializePrimitive(SerializeType):
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

class SerializeObject(SerializeType):
    """A serializable non-primitive object."""
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

class SerializeArray(SerializeType):
    """Represents an array whose elements are of homogeneous type."""

    def __init__(self, type):
        """Constructor.

        PARAMETERS:
        type -- SerializeType; for example, to create an array of
                an Object, the type should be SerializeObject(Object)
        """
        self._type = type

    @property
    def type(self):
        """The type of object represented by this array."""
        return self._type

    @property
    def default(self):
        return []

    def validate(self, obj):
        return (type(obj) in (list, tuple)
                and all(self._type.validate(elem) for elem in obj))

    def __str__(self):
        return 'list of ' + str(self._type)

class SerializeMap(SerializeType):
    """Represents an array whose elements are of homogeneous type."""

    def __init__(self, fields):
        """Constructor.

        PARAMETERS:
        fields -- dict; keys are valid dictionary values, values are
                  SerializeTypes.
        """
        self._fields = fields

    @property
    def default(self):
        return {k: v.default for k, v in self._fields.items()}

    def validate(self, obj):
        return (type(obj) == dict
                and set(obj) == set(self._fields)
                and all(self._fields[k].validate(obj[k]) for k in obj))

    def __str__(self):
        return 'dictionary'

BOOL_FALSE = SerializePrimitive(False, bool)
BOOL_TRUE = SerializePrimitive(True, bool)
INT = SerializePrimitive(0, int)
FLOAT = SerializePrimitive(0, float, int)
STR = SerializePrimitive('', str)
DICT = SerializeObject(dict)
LIST = SerializeObject(list)
