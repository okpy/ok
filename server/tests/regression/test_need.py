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

from app.needs import Need
from app.exceptions import *
from test_base import BaseTestCase


class NeedTestCase(BaseTestCase):

	def test_get_message_type(self):
		""" Tests that for type """
		need = Need('get').set_object(str).get_exception_message()
		self.assertIn('get', need)
		self.assertIn('str', need)

	def test_get_message_object(self):
		""" Tests for objects """
		obj = self.obj()
		need = Need('get').set_object(obj).get_exception_message()
		self.assertIn('get', need)
		self.assertIn('instance', need)

	def test_get_message_falsey(self):
		""" Tests for falsey objects """
		need = Need('get')
		self.assertIn('unknown object', need.set_object(False).get_exception_message())
		self.assertIn('unknown object', need.set_object([]).get_exception_message())
		self.assertIn('unknown object', need.set_object(0).get_exception_message())
