#!/usr/bin/env python
# encoding: utf-8
"""
Tests api field filtering.
"""
import os
os.environ['FLASK_CONF'] = 'TEST'
from app.utils import coerce_to_json
from test_base import BaseTestCase, unittest

class FakeModel(object):
    """
    Test class that fakes out to_json
    """

    num = 0
    def __init__(self):
        self.num = FakeModel.num
        FakeModel.num += 1

    def to_json(self, fields=None):
        return 'json' + str(self.num)

class FieldsTest(BaseTestCase):
    """
    Tests for api fields feature.
    """
    def setUp(self):
        super(FieldsTest, self).setUp()
        FakeModel.num = 0

    def coerce(self, data, fields=None):
        if not fields:
            fields = {}
        self.data = coerce_to_json(data, fields)

    def test_basic_all(self):
        """
        Tests coercing a basic value.
        """
        self.coerce(FakeModel())
        self.assertEquals('json0', self.data)

    def test_list_all(self):
        """
        Tests coercing a list.
        """
        self.coerce([FakeModel(), FakeModel()])
        self.assertEquals(['json0', 'json1'], self.data)

    def test_dict_all(self):
        """
        Tests coercing a dictionary.
        """
        self.coerce({
            'a': FakeModel(),
            'b': FakeModel()
        })
        self.assertEquals({
            'a': 'json0',
            'b': 'json1'
        }, self.data)

    def test_nested_all(self):
        """
        Tests coercing a nested structure.
        """
        self.coerce({
            'a': {
                'd': FakeModel(),
                'e': FakeModel()
            },
            'b': FakeModel()
        })
        self.assertEquals({
            'a': {
                'd': 'json0',
                'e': 'json1',
            },
            'b': 'json2',
        }, self.data)

    def test_nested_fields(self):
        """
        Tests coercing a nested structure with filtering fields.
        """
        test_self = self
        class TestModel(object):
            def to_json(self, fields):
                test_self.assertEqual(fields, ['foo'])

        self.coerce({
            'a': {
                'b': TestModel(),
            }
        }, {'a': {'b': ['foo']}})


if __name__ == '__main__':
    unittest.main()

