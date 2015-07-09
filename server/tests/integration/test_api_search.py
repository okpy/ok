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

import datetime
from test_base import APIBaseTestCase, unittest, api #pylint: disable=relative-import
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils
from ddt import ddt, data, unpack
from app.exceptions import *
from integration.test_api_base import APITest
import operator as op


class SearchAPITest(APIBaseTestCase):

	API = api.SearchAPI

	def setUp(self):
		super(SearchAPITest, self).setUp()
		self.assignment_name = 'Hog Project'
		self.user = self.accounts['dummy_student2']
		self._course = make_fake_course(self.user)
		self._course.put()
		self._assign = make_fake_assignment(self._course, self.user)
		self._assign.name = self._assign.display_name = self.assignment_name
		self._assign.put()
		self._backup = make_fake_backup(self._assign, self.user)
		self._submission = make_fake_submission(self._backup)
		self._finalsubmission = make_fake_finalsubmission(self._submission, self._assign, self.user)

	def get_accounts(self):
		return APITest().get_accounts()

	############
	# TOKENIZE #
	############

	def test_tokenize_basic(self):
		""" Tests that the single-dash is parsed normally. """
		query = '-assignment Hog'
		tokens = self.API.tokenize(query)
		self.assertTrue('assignment' in tokens[0])
		self.assertTrue('Hog' in tokens[0])

	def test_tokenize_operator(self):
		""" Tests that both flag and operator are parsed normally. """
		query = '-assignment --startswith Hog'
		tokens = self.API.tokenize(query)
		self.assertTrue('assignment' in tokens[0])
		self.assertTrue('Hog' in tokens[0])
		self.assertTrue('startswith' in tokens[0])

	def test_tokenize_dashes(self):
		""" Tests that dashes inside the arg are okay. """
		query = '-date --before 2015-06-22'
		tokens = self.API.tokenize(query)
		self.assertTrue('date' in tokens[0])
		self.assertTrue('before' in tokens[0])
		self.assertTrue('2015-06-22' in tokens[0])

	def test_tokenize_quoted_string(self):
		""" Tests that args with spaces can be grouped by quotations """
		query = '-assignment "Hog Project"'
		tokens = self.API.tokenize(query)
		self.assertTrue('assignment' in tokens[0])
		self.assertTrue('Hog Project' in tokens[0])

	def test_tokenize_single_quoted_string(self):
		""" Tests that args with spaces can be grouped by single quotations """
		query = "-assignment 'Hog Project'"
		tokens = self.API.tokenize(query)
		self.assertTrue('assignment' in tokens[0])
		self.assertTrue('Hog Project' in tokens[0])

	def test_multiple_flags(self):
		""" Tests that the multiple groups can be parsed together. """
		query = '-assignment Hog -date --before 2015-06-22'
		tokens = self.API.tokenize(query)
		self.assertTrue('assignment' in tokens[0])
		self.assertTrue('Hog' in tokens[0])
		self.assertTrue('date' in tokens[1])
		self.assertTrue('before' in tokens[1])
		self.assertTrue('2015-06-22' in tokens[1])

	def test_datatype_int(self):
		""" Tests that integers are parsed normally. """
		query = '-price 10'
		tokens = self.API.tokenize(query)
		self.assertTrue('price' in tokens[0])
		self.assertTrue('10' in tokens[0])

	def test_datatype_boolean(self):
		""" Tests that booleans are parsed normally. """
		query = '-pricey true'
		tokens = self.API.tokenize(query)
		self.assertTrue('pricey' in tokens[0])
		self.assertTrue('true' in tokens[0])

	def test_single_character_arg(self):
		""" Tests that an arg with only length one can be parsed normally. """
		query = '-price 1'
		tokens = self.API.tokenize(query)
		self.assertTrue('price' in tokens[0])
		self.assertTrue('1' in tokens[0])

	def test_laziness_with_quotations(self):
		""" Tests that quotations are lazily matched """
		query = '-date --before "2015-06-22" -assignment "Homework 1"'
		tokens = self.API.tokenize(query)
		self.assertTrue('date' in tokens[0])
		self.assertTrue('before' in tokens[0])
		self.assertTrue('2015-06-22' in tokens[0])
		self.assertTrue('assignment' in tokens[1])
		self.assertTrue('Homework 1' in tokens[1])

	#######################
	# TRANSLATE OPERATORS #
	#######################

	def test_translate_basic(self):
		""" Basic extraction of arg and operator """
		query = '-date --before 2015-06-22'
		scope = self.API.translate(query)
		operator, arg = scope['date']
		self.assertEqual(operator, op.__lt__)
		self.assertEqual(arg, '2015-06-22')

	def test_translate_operators(self):
		""" Translate to eq if no operator specified """
		query = '-assignment Scheme'
		scope = self.API.translate(query)
		operator, arg = scope['assignment']
		self.assertEqual(operator, op.__eq__)
		self.assertEqual(arg, 'Scheme')

	#################
	# QUERY RESULTS #
	#################

	def test_flag_onlyfinal(self):
		""" Testing if onlyfinal flag operates without error """
		query = '-assignment "%s" -onlyfinal %s'
		self.API.querify(query % (self.assignment_name, 'true'))
		self.API.querify(query % (self.assignment_name, 'false'))

	def test_flag_onlyfinal_with_quotations(self):
		""" Testing if onlyfinal flag with double quotations operates without error """
		query = '-date --after "2015-06-22" -assignment "%s" -onlyfinal %s'
		self.API.querify(query % (self.assignment_name, 'true'))
		self.API.querify(query % (self.assignment_name, 'false'))

	def test_flag_onlybackup(self):
		""" Testing if onlybackup flag operates without error """
		query = '-assignment "%s" -onlybackup %s'
		self.API.querify(query % (self.assignment_name, 'true'))
		self.API.querify(query % (self.assignment_name, 'false'))

	def test_flag_onlybackup_results(self):
		""" Testing if onlybackup actually returns ONLY backups. """
		query = '-assignment "%s" -onlybackup true' % self.assignment_name
		results = self.API.querify(query).fetch()
		self.assertTrue(len(results) > 0)

		for result in results:
			self.assertTrue(isinstance(result, models.Backup))

	def test_flag_onlyfinal_results(self):
		""" Testing if onlybackup actually returns ONLY backups. """
		query = '-assignment "%s" -onlyfinal true' % self.assignment_name
		results = self.API.querify(query).fetch()
		self.assertTrue(len(results) > 0)

		for result in results:
			self.assertTrue(isinstance(result, models.FinalSubmission))

	def test_flag_onlybackup_negated(self):
		""" Testing that onlybackup negated does not limit results. """
		query = '-assignment "%s" -onlybackup false' % self.assignment_name
		results = self.API.querify(query).fetch()
		self.assertTrue(len(results) > 0)

		backups = [result for result in results if isinstance(result, models.Backup)]
		self.assertNotEqual(backups, results)

	def test_flag_onlyfinal_negated(self):
		""" Testing that onlyfinal negated does not limit results. """
		query = '-assignment "%s" -onlyfinal false' % self.assignment_name
		results = self.API.querify(query).fetch()
		self.assertTrue(len(results) > 0)

		finals = [result for result in results if isinstance(result, models.FinalSubmission)]
		self.assertNotEqual(finals, results)
