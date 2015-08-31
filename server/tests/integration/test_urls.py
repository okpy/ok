#!/usr/bin/env python
# encoding: utf-8

"""
Tests for the permissions system
"""

import os
os.environ['FLASK_CONF'] = 'TEST'
import datetime
import urllib
import flask

from flask import request

from werkzeug.wrappers import Response

from test_base import APIBaseTestCase, unittest, make_fake_course, Mock, mock #pylint: disable=relative-import

from app import app
from app import models, utils, urls, constants, auth, api

from google.appengine.api import users
from google.appengine.ext import ndb

from app import auth
from app.exceptions import *
from app.authenticator import Authenticator, AuthenticationException


def register_api_test(f):
	""" Swaps out add_url_rule so flask doesn't complain """
	def helper(*args, **kwargs):
		real_addurlrule = app.add_url_rule
		app.add_url_rule = lambda *args, **kwargs: None
		response = f(*args, **kwargs)
		app.add_url_rule = real_addurlrule
		return response
	helper.__name__ = f.__name__
	return helper


class URLsUnitTest(APIBaseTestCase):

	url_prefix = ''

	def get_accounts(self):
		"""
		Returns the accounts you want to exist in your system.
		"""
		return {
			"student0": models.User(
				email=["dummy@student.com"]
			),
			"student1": models.User(
				email=["other@student.com"]
			),
			"staff": models.User(
				email=["dummy@staff.com"]
			),
			"admin": models.User(
				email=["dummy@admin.com"],
				is_admin=True
			),
			"dummy_admin": models.User(
				email=["dummy3@admin.com"],
				is_admin=True
			)
		}

	def assertStatusCode(self, code): #pylint: disable=invalid-name
		self.assertEqual(
			self.response.status_code, code,
			'response code ({}) != correct code ({}).\n{}'.format(
				self.response.status_code, code,
				self.response.get_data()[:100]))

	def setUp(self):
		super(URLsUnitTest, self).setUp()
		self.accounts = self.get_accounts()
		for user in self.accounts.values():
			user.put()
		self._course = make_fake_course(self.accounts['admin'])
		self._course.put()
		self.user = None

	def test_force_account_chooser(self):
		""" Simple test for repl """
		url_ok = 'http://okpy.org'
		self.assertEqual(urls.force_account_chooser(url_ok), url_ok)

		url_notok = 'http://google.com/ServiceLogin'
		self.assertEqual(
			urls.force_account_chooser(url_notok),
			url_notok.replace('ServiceLogin', 'AccountChooser')
		)

	def get_home(self):
		""" Access homepage """
		return self.get('/')

	def get_landing(self):
		""" Access landing """
		return self.get('/landing')

	def get_login(self):
		""" Access login """
		return self.get('/login')

	def get_manage(self):
		""" Access administrator panel """
		return self.get('/manage')

	# home page

	def test_home_not_logged_in(self):
		""" Tests that user not logged in is sent to login """
		self.get_home()
		self.assertStatusCode(302)

	def test_home_logged_in(self):
		""" Tests that logged in student stays on page """
		self.login('student0')
		self.get_home()
		self.assertStatusCode(200)

	def test_home_logged_in_content(self):
		""" Tests that content for home is accurate """
		self.login('student0')
		self.get_home()
		html, user = self.response.response[0], self.accounts['student0']
		self.assertIn(str(user.key.id()), html)
		self.assertIn(user.email[0], html)
		self.assertIn(users.create_logout_url('/landing'), html)
		self.assertIn('Log Out', html)
		self.assertIn(users.create_logout_url(
			urls.force_account_chooser(users.create_login_url('/'))
		), html)

	# landing

	def test_landing_without_login(self):
		""" Tests that landing shows login info for non-logged-in user """
		self.get_landing()
		self.assertStatusCode(200)
		html, user = self.response.response[0], self.accounts['student0']
		self.assertIn(urls.force_account_chooser(users.create_login_url('/')), html)
		self.assertIn('Sign In', html)

	def test_landing_with_login(self):
		""" Tests that landing shows dashboard info for logged-in user """
		self.login('student0')
		self.get_landing()
		self.assertStatusCode(200)
		html, user = self.response.response[0], self.accounts['student0']
		self.assertIn(str(user.key.id()), html)
		self.assertIn('Student Dashboard', html)
		self.assertIn(users.create_logout_url('/landing'), html)
		self.assertIn('Log Out', html)

	# login

	def test_login_without_login(self):
		""" Tests that login shows without logged-in user """
		self.get_login()
		self.assertStatusCode(302)

	def test_login_with_login(self):
		""" Tests that user redirected home with logged-in user """
		self.login('student0')
		self.get_login()
		self.assertStatusCode(302)

	# manage

	def test_manage_without_login(self):
		""" Tests that a user not logged in is sent to login """
		self.get_manage()
		self.assertStatusCode(302)

	def test_manage_with_student(self):
		""" Tests that a student cannot access admin """
		self.login('student0')
		self.get_manage()
		self.assertStatusCode(404)

	def test_manage_with_admin(self):
		""" Tests that admin can access admin panel """
		self.login('admin')
		self.get_manage()
		self.assertStatusCode(200)

	# errors

	def test_server_error(self):
		""" Tests that server_error behaves normally """
		with self.app.test_request_context('/landing'):
			message = self.obj().set(get_exception_message='Some message')
			response, status_code = urls.server_error(PermissionError(message))
			self.assertEqual(status_code, 500)

	def test_args_error(self):
		""" Tests that args_error raises an error """
		with self.assertRaises(BadValueError):
			message = self.obj().set(get_exception_message=lambda: 'Some message')
			urls.args_error(PermissionError(message))

	def test_version_exception(self):
		""" Tests that no versions throws error """
		with self.assertRaises(APIException):
			urls.check_version('1.0')

	# register_api

	def api_wrapper(self):
		""" Returns nested function, api_wrapper in register_api """
		return urls.register_api(api.APIResource, 'fake_api', 'fake')

	@register_api_test
	def test_api_incorrect_version_error(self):
		""" Tests that IVE is caught """
		with self.app.test_request_context('/api/v1/'):
			models.Version(
				name='ok',
				base_url='HAH',
				current_version='0.9').put()
			request.args = {'client_version': '0.8'}
			response = self.api_wrapper()()
			self.assertEqual(response.status_code, 403)

	@register_api_test
	def test_api_checks_version(self):
		""" Tests that version is checked """
		with self.app.test_request_context('/api/v1/'):
			request.args = {'client_version': '0.8'}
			response = self.api_wrapper()()
			self.assertEqual(response.status_code, 400)

	@register_api_test
	def test_api_user_returned(self):
		""" Tests that user is returned """
		with self.app.test_request_context('/api/v1/'):
			real_auth = auth.authenticate
			auth.authenticate = lambda: 1
			self.assertEqual(1, self.api_wrapper()())
			auth.authenticate = real_auth

	@register_api_test
	def test_api_500_exception(self):
		""" Induce a 500 error """
		with self.app.test_request_context('/api/v1/'):
			real_auth = auth.authenticate
			auth.authenticate = self.raise_error
			self.assertEqual(500, self.api_wrapper()().status_code)
			auth.authenticate = real_auth

	@register_api_test
	def test_api_rval_response(self):
		""" Tests that werkzeug rvals are not changed """
		rval = Response()
		self.mock(auth, 'authenticate').using(lambda: models.User())
		self.mock(api.APIResource, 'as_view').using(staticmethod(
			lambda _: lambda *args, **kwargs: rval))
		with self.app.test_request_context('/api/v1/'):
			self.assertTrue(isinstance(rval, Response))
			self.assertFalse(isinstance(rval, flask.Response))
			api_wrapper = urls.register_api(api.APIResource, 'fake_api', 'fake')
			response = api_wrapper()
			self.assertTrue(isinstance(rval, Response))
			self.assertFalse(isinstance(rval, flask.Response))
			self.assertEqual(response, rval)

	@register_api_test
	def test_api_rval_response_list(self):
		""" Tests that werkzeug rvals are not changed """
		self.mock(auth, 'authenticate').using(lambda: models.User())
		self.mock(api.APIResource, 'as_view').using(staticmethod(
			lambda _: lambda *args, **kwargs: [1, 2, 3]))
		with self.app.test_request_context('/api/v1/'):
			api_wrapper = urls.register_api(api.APIResource, 'fake_api', 'fake')
			response = api_wrapper(test=True)
			self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
	unittest.main()
