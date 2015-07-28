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

from app import models
from app.exceptions import *
import json
from test_base import BaseTestCase
from mock import MagicMock


class ModelsTestCase(BaseTestCase):
	
	# Utilities

	def test_JSONEncoder(self):
		""" Tests that objects invokes to_json """
		user = models.User(email=['yo@yo.com']).put()
		models.JSONEncoder(user)
	
	def testBase_tojson(self):
		""" Tests that to_json returns a dict """
		user = models.User(email=['yo@yo.com']).put().get()
		assert isinstance(user.to_json(), dict)
		assert isinstance(user.to_json(True), dict)
		self.assertEqual(user.to_json(False), {})
		self.assertEqual(user.to_json({'email': ''}),
			{'email': ['yo@yo.com']})
		
		user.to_dict = MagicMock(returnvalue={'treasure': [user.key]})
		user.to_json({'treasure': True})
		
	def testBase_defaultPermission(self):
		""" Tests that default is False """
		self.assertFalse(models.Base._can(*([None]*4)))
		
	# UserModel
	
	def test_contains_files(self):
		""" Tests that contains_files works """
		backup_with = MagicMock()
		backup_with.get_messages.return_value = {
			'file_contents': 'HUEHUE'
		}
		backup_without = MagicMock()
		backup_without.get_messages.return_value = {}
		user = models.User()
		self.assertEqual({'file_contents': 'HUEHUE'}, 
		                 backup_with.get_messages())
		self.assertEqual(user._contains_files(backup_with), 'HUEHUE')
		self.assertEqual(user._contains_files(backup_without), None)
		
	def test_get_backups_helper_notin_group(self):
		""" Test self not in group """
		user = models.User(email=['yo@yo.com']).put().get()
		magic = MagicMock()
		magic.member = {}
		user.get_group = magic
		user._get_backups_helper(None)
		user.get_group.assert_called_with(None)
		
	def test_get_submissions_helper_notin_group(self):
		""" Test self not in group """
		user = models.User(email=['yo@yo.com']).put().get()
		magic = MagicMock()
		magic.member = {}
		user.get_group = magic
		user._get_submissions_helper(None)
		user.get_group.assert_called_with(None)