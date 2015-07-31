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
from app.needs import Need
from app.exceptions import *
import json
from test_base import BaseTestCase
from mock import MagicMock
from google.appengine.ext import ndb


class ModelsTestCase(BaseTestCase):
	
	# Utilities

	def test_JSONEncoder(self):
		""" Tests that objects invokes to_json """
		user = models.User(email=['yo@yo.com']).put()
		assert isinstance(user, ndb.Key)
		models.JSONEncoder().default(user)
	
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
		
	def test_get_backups_helper_in_group(self):
		""" Test self not in group """
		user = models.User(email=['yo@yo.com']).put().get()
		user.get_group = MagicMock(
			return_value=MagicMock(
				member=[user.key]))
		user._get_backups_helper(None)

		user.get_group.assert_called_with(None)
		assert user.key in user.get_group(None).member
		
	def test_get_submissions_helper_in_group(self):
		""" Test self not in group """
		user = models.User(email=['yo@yo.com']).put().get()
		user.get_group = MagicMock(
			return_value=MagicMock(
				member=[user.key]))
		user._get_submissions_helper(None)

		user.get_group.assert_called_with(None)
		assert user.key in user.get_group(None).member
		
	def test_can_lookup(self):
		"""Tests that anyone can lookup"""
		user = models.User(email=['yo@yo.com']).put().get()
		need = Need('lookup')
		self.assertTrue(user._can(user, need, None, None))
		
	def test_can_get_not_user(self):
		"""Tests can get with invalid user"""
		user = models.User(email=['yo@yo.com']).put().get()
		need = Need('get')
		self.assertFalse(user._can(user, need, None, None))
		
	def test_can_index(self):
		"""Tests that index only works for user"""
		user = models.User(email=['yo@yo.com']).put().get()
		need = Need('index')
		self.assertTrue(user._can(user, need, None,
		                           MagicMock(filter=lambda *args: True)))
		
	def test_pre_put_hook(self):
		"""Tests that pre put hook for user works"""
		with self.assertRaises(BadValueError):
			models.User().put()
			
	def test_scores_forassign_wo_fs(self):
		"""Tests that missing fs doesn't crash method"""
		assign = models.Assignment().put().get()
		user = models.User(email=['yo@yo.com']).put().get()
		self.assertEqual(
			user.scores_for_assignment(assign),
			([[user.email[0], 0, None, None, None]], False))
		
	def test_scores_forassign_w_fs_wo_scores(self):
		"""Tests that fs scores are loaded"""
		assign = models.Assignment().put()
		user = models.User(email=['yo@yo.com']).put()
		backup = models.Backup(submitter=user, assignment=assign).put()
		subm = models.Submission(backup=backup).put()
		models.FinalSubmission(
			submitter=user, 
			assignment=assign, 
			submission=subm).put()
		
		user = user.get()
		self.assertNotEqual(user.get_final_submission(assign), None)
		self.assertFalse(user.scores_for_assignment(assign.get())[1])

	def test_scores_forassign_w_fs_w_scores(self):
		"""Tests that fs scores are loaded"""
		assign = models.Assignment().put()
		user = models.User(email=['yo@yo.com']).put()
		backup = models.Backup(submitter=user, assignment=assign).put()
		score = models.Score(score=10, grader=user)
		subm = models.Submission(
			backup=backup,
			score=[score]).put()
		models.FinalSubmission(
			submitter=user,
			assignment=assign,
			submission=subm).put()

		user = user.get()
		self.assertNotEqual(user.get_final_submission(assign), None)
		self.assertTrue(user.scores_for_assignment(assign.get())[1])