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
from app.exceptions import *
from test_base import BaseTestCase
from google.appengine.ext import ndb


class TestingError(Exception):
	pass


class APITestCase(BaseTestCase):
	"""
	Testing API utilities
	"""
	
	def raise_error(self):
		raise TestingError()

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
	
	def test_key_repeated_arg_list(self):
		""" Tests that key_repeated_arg accepts list"""
		cls, ids = 'Submission', [1, 2, 3]
		arg = api.KeyRepeatedArg(cls)
		lst = arg.use(ids)
		assert isinstance(lst, list)

		for i, item in enumerate(lst):
			assert isinstance(item, ndb.Key)
			assert item.id() == ids[i]

	def test_key_repeated_arg_string(self):
		""" Tests that key_repeated_arg accepts string"""
		cls, ids_str, ids = 'Submission', '1, 2, 3', [1, 2, 3]
		arg = api.KeyRepeatedArg(cls)
		lst = arg.use(ids_str)
		assert isinstance(lst, list)

		for i, item in enumerate(lst):
			assert isinstance(item, ndb.Key)
			assert item.id() == ids[i]
			
	def test_key_repeated_arg_string_single(self):
		""" Tests that key_repeated_arg accepts non-CSV """
		cls, ids_str, ids = 'Submission', '1', [1]
		arg = api.KeyRepeatedArg(cls)
		lst = arg.use(ids_str)
		assert isinstance(lst, list)
		
		for i, item in enumerate(lst):
			assert isinstance(item, ndb.Key)
			assert item.id() == ids[i]

	def test_key_repeated_arg_string_single_string(self):
		""" Tests that key_repeated_arg accepts non-CSV """
		cls, ids_str, ids = 'Submission', 'hello', ['hello']
		arg = api.KeyRepeatedArg(cls)
		lst = arg.use(ids_str)
		assert isinstance(lst, list)

		for i, item in enumerate(lst):
			assert isinstance(item, ndb.Key)
			assert item.id() == ids[i]

	def test_key_repeated_arg_string_string(self):
		""" Tests that key_repeated_arg accepts string"""
		cls, ids_str, ids = 'Submission', 'hello,world,hi', ['hello', 'world', 'hi']
		arg = api.KeyRepeatedArg(cls)
		lst = arg.use(ids_str)
		assert isinstance(lst, list)

		for i, item in enumerate(lst):
			assert isinstance(item, ndb.Key)
			assert item.id() == ids[i]
			
	def test_boolean_arg(self):
		""" Tests that boolean arg converts correctly """
		arg = api.BooleanArg()
		assert arg.use('false') is False
		assert arg.use('true') is True
		with self.assertRaises(BadValueError):
			arg.use('True')
			
	################
	# API RESOURCE #
	################
	
	def obj(self):
		""" Utility - object with set(k=v, k2=v2) method """
		class Obj:
			def set(self, **kwargs):
				[setattr(self, k, v) for k, v in kwargs.items()]
				return self
		return Obj()
	
	def always_can(self):
		""" Utility - object that always allows user """
		return self.obj().set(can=lambda *args, **kwargs: True)
		
	def never_can(self):
		""" Utility - object that never allows user """
		return self.obj().set(can=lambda *args, **kwargs: False)
		
	def test_apiresource_name(self):
		""" Tests that model name is returned """
		subm = api.FinalSubmissionAPI()
		self.assertEqual(subm.name, 'FinalSubmission')
		
	def test_apiresource_get_instance(self):
		""" Tests that get_instance checks permissions """
		apre = api.APIResource()
		with self.assertRaises(PermissionError):
			apre.model = self.obj().set(
				get_by_id=lambda *args: self.never_can())
			apre.get_instance('some_key', None)
		
	def test_apiresource_call_method_invalid_method(self):
		""" Tests that invalid method is intercepted """
		with self.assertRaises(BadMethodError):
			apre = api.APIResource()
			apre.call_method('dne', None, None)
	
	# def test_dispatch_request_bad_http(self):
	# 	""" Tests that only 'get' and 'post' are allowed for index """
	# 	from flask import app
	# 	apre = api.APIResource()
	# 	app.request = self.obj().set(method='put')
	# 	with self.assertRaises(IncorrectHTTPMethodError):
	# 		apre.dispatch_request(None)
	
	def test_apiresource_http_required(self):
		""" Tests that constraints function """
		with self.assertRaises(IncorrectHTTPMethodError):
			apre = api.APIResource()
			apre.methods = {
				'multiply': {
					'methods': set(['PUT', 'GET'])
				}
			}
			apre.call_method('multiply', None, 'POST')
		
	def test_apiresource_http_not_specified(self):
		""" Tests that http method is checked for existence """
		with self.assertRaises(IncorrectHTTPMethodError):
			apre = api.APIResource()
			apre.methods = {
				'multiply': {
					'methods': set(['PUT', 'GET'])
				}
			}
			apre.call_method('multiply', None, None)
			
	def test_put_checks(self):
		""" Tests that put checks for permissions """
		with self.assertRaises(PermissionError):
			apre = api.APIResource()
			apre.put(self.never_can(), None, {})
			
	def test_put_check_blank_val(self):
		""" Tests that put does not set invalid fields """
		apre = api.APIResource()
		status, message = apre.put(self.always_can(), None, {'funny': 'beans'})
		self.assertEqual(400, status)
		
	def test_put_with_change(self):
		""" Tests that if there is change, there is put"""
		obj = self.always_can()
		obj.put = self.raise_error
		obj.var = 'a'
		data = {'var': 'b'}
		apre = api.APIResource()
		with self.assertRaises(TestingError):
			apre.put(obj, None, data)

	def test_put_without_change(self):
		""" Tests that if there is no change, there is no put"""
		obj = self.always_can()
		obj.put = self.raise_error
		obj.var = 'a'
		apre = api.APIResource()
		apre.put(obj, None, {})
		assert True  # put was not invoked
		self.assertEqual(obj.var, 'a')

	def test_put_effects_change(self):
		""" Tests that put updates the obj"""
		obj = self.always_can()
		obj.put = lambda: '_'
		obj.var = 'a'
		data = {'var': 'b'}
		apre = api.APIResource()
		apre.put(obj, None, data)
		self.assertEqual(obj.var, 'b')
		
	def test_post_checks(self):
		""" Tests that post checks for permissions """
		apre = api.APIResource()
		apre.model = self.never_can()
		apre.new_entity = lambda *args, **kwargs: '_'
		with self.assertRaises(PermissionError):
			apre.post(None, {})

	def test_delete_checks(self):
		""" Tests that post checks for permissions """
		apre = api.APIResource()
		apre.model = self.never_can()
		with self.assertRaises(PermissionError):
			apre.delete(None, None, {})
			
	def test_delete_invoked(self):
		""" Tests that delete is invoked """
		apre = api.APIResource()
		apre.model = self.always_can()
		apre.model.key = self.obj().set(delete=self.raise_error)
		with self.assertRaises(TestingError):
			apre.delete(apre.model, None, {})
			
	def test_index(self):
		""" Tests that index checks for result """
		apre = api.APIResource()
		apre.model = self.obj().set(
			can=lambda *args, **kwargs: None,
			query=lambda: None)
		with self.assertRaises(PermissionError):
			apre.index(None, {})
			
	def test_parse_args_limit_types(self):
		""" Tests that parse_args only accepts dictionaries and booleans """
		apre = api.APIResource()
		api.parser = self.obj().set(
			parse=lambda *args: {'fields': 'invalid type'}
		)
		with self.assertRaises(BadValueError):
			apre.parse_args(None, None)
			
	def test_statistics_blank(self):
		""" Tests that empty dictionary returned if stat is none """
		apre = api.APIResource()
		apre.model = lambda: '_'
		self.assertNotIn('total', apre.statistics())
		
	def test_statistics_with_total(self):
		""" Tests that dictionary with data returned if otherwise """
		model_name = 'User'
		apre = api.APIResource()
		apre.model = self.obj().set(__name__=model_name)
		api.stats.KindStat(kind_name=model_name).put()
		self.assertIn('total', apre.statistics())