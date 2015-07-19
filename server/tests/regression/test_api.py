#!/usr/bin/env python
# encoding: utf-8
#pylint: disable=no-member, no-init, too-many-public-methods
#pylint: disable=attribute-defined-outside-init
# This disable is because the tests need to be name such that
# you can understand what the test is doing from the method name.
#pylint: disable=missing-docstring
"""
tests.py

"""

from app import api
from test_base import BaseTestCase


class APITestCase(BaseTestCase):
	"""
	Testing API utilities
	"""

	##################
	# JSON ET. MISC. #
	##################

	def test_parse_json_field_bool(self):
		""" Tests that bool 'parsed' correctly """
		self.assertFalse(api.parse_json_field('false'))
		self.assertTrue(api.parse_json_field('true'))
		
	def test_parse_json_field_nonbool(self):
		""" Tests that JSON parsed correctly """
		self.assertEqual(api.parse_json_field('{"hi":"yo"}')['hi'], 'yo')
		
	def test_parse_json_list_field(self):
		""" Tests taht bool 'parsed' correctly """
		self.assertFalse(api.parse_json_list_field('false'))
		self.assertTrue(api.parse_json_list_field('true'))

	def test_parse_json_list_field_nonbool(self):
		""" Tests that JSON parsed correctly """
		assert len(api.parse_json_list_field('[1,2,3,4,5]')) == 5
		
	def test_parse_json_either(self):
		""" Tests that either parse can be used interchangeaby """
		assert len(api.parse_json_field('[1,2,3,4,5]')) == 5
		self.assertEqual(api.parse_json_list_field('{"hi":"yo"}')['hi'], 'yo')
		
	def test_parse_json_field(self):
		""" Tests that neither lists nor dictionaries are left alone """
		self.assertEqual(api.parse_json_field('hello'), 'hello')
		
	def test_try_int(self):
		""" Tests that try_int doesn't die """
		assert api.try_int('5') == 5
		assert api.try_int('uh oh') == 'uh oh'
		assert api.try_int(['a', 'b']) == ['a', 'b']
		
	########
	# ARGS #
	########
	
	def test_key_repeated_arg(self):
		""" Tests that key_repeated_arg gives list"""
		pass