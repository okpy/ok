from exceptions.serialize import DeserializeError
from models import serialize
from unittest import mock
import unittest

class MockSerializable(serialize.Serializable):
    REQUIRED = {
        'bool': serialize.BOOL_FALSE,
        'int': serialize.INT,
    }
    OPTIONAL = {
        'string': serialize.STR,
        'list': serialize.LIST,
    }

class SerializableTest(unittest.TestCase):
    def testConstructor_missingRequiredFields(self):
        self.assertRaises(DeserializeError, MockSerializable)

    def testConstructor_incorrectRequiredFields(self):
        self.assertRaises(DeserializeError, MockSerializable,
                          bool=0, int=False)

    def testConstructor_incorrectOptionalFields(self):
        self.assertRaises(DeserializeError, MockSerializable,
                          bool=0, int=False, string=0)

    def testConstructor_unexpectedFields(self):
        self.assertRaises(DeserializeError, MockSerializable,
                          bool=0, int=False, foo=0)

    def testGetItem(self):
        serializable = MockSerializable(bool=True, int=9001)
        self.assertEqual(True, serializable['bool'])
        self.assertEqual(9001, serializable['int'])

    def testGetItem_keyError(self):
        serializable = MockSerializable(bool=True, int=9001)
        self.assertRaises(KeyError, serializable.__getitem__, 'foo')

    def testSetItem(self):
        serializable = MockSerializable(bool=True, int=9001)
        serializable['int'] = 42
        self.assertEqual(42, serializable['int'])

    def testSetItem_invalidtype(self):
        serializable = MockSerializable(bool=True, int=9001)
        self.assertRaises(DeserializeError, serializable.__setitem__,
                          'int', False)

class SerializeArrayTest(unittest.TestCase):
    def testValidate_correctType(self):
        array = serialize.SerializeArray(serialize.INT)
        self.assertTrue(array.validate([4, 3, 2, 1]))

    def testValidate_incorrectType(self):
        array = serialize.SerializeArray(serialize.INT)
        self.assertFalse(array.validate([4, True, 2, 1]))

    def testValidate_recursiveCorrectType(self):
        array = serialize.SerializeArray(
                    serialize.SerializeArray(serialize.INT))
        self.assertTrue(array.validate([[1, 2], [3]]))

    def testValidate_recursiveIncorrectType(self):
        array = serialize.SerializeArray(
                    serialize.SerializeArray(serialize.INT))
        self.assertFalse(array.validate([[1, False], [3]]))

class SerializeMapTest(unittest.TestCase):
    def setUp(self):
        self.map = serialize.SerializeMap({
            'foo': serialize.INT,
            'bar': serialize.BOOL_FALSE,
        })

    def testDefault(self):
        self.assertEqual({
            'foo': serialize.INT.default,
            'bar': serialize.BOOL_FALSE.default,
        }, self.map.default)

    def testValidate_correctType(self):
        self.assertTrue(self.map.validate({'foo': 9001, 'bar': True}))

    def testValidate_incorrectType(self):
        self.assertFalse(self.map.validate({'foo': False, 'bar': True}))

    def testValidate_invalidKey(self):
        self.assertFalse(self.map.validate({'foo': 9001, 'bar': True, 'garply': 5}))

    def testValidate_missingKey(self):
        self.assertFalse(self.map.validate({'foo': 9001}))
