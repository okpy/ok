from test_base import auth, BaseTestCase, models

from app.authenticator import TestingAuthenticator, AuthenticationException, GoogleAuthenticator

import requests


class AuthTestCase(BaseTestCase):
	"""
	Testing authenticator
	"""

	response = '{}'
	access_token = 'gibberish'

	def test_testing_authenticator(self):
		self.assertEqual(TestingAuthenticator().authenticate(self.access_token), self.access_token)

	def setup_response(self, response):
		resp = lambda: '_'
		resp.json = lambda: response
		requests.get = lambda x, params: resp

	def test_google_authenticator_error(self):
		""" Test Google auth error """
		self.setup_response({'error': 'uh oh'})
		try:
			GoogleAuthenticator().authenticate(self.access_token)
			assert False
		except AuthenticationException as e:
			self.assertEqual('access token invalid', str(e))

	def test_google_authenticator_no_email(self):
		""" Test Google auth missing email """
		self.setup_response({})
		try:
			GoogleAuthenticator().authenticate(self.access_token)
			assert False
		except AuthenticationException as e:
			self.assertEqual('email doesn\'t exist', str(e))

	def test_google_authenticator_success(self):
		""" Test Google auth success """
		email ='test@example.com'
		self.setup_response({'email': email})
		self.assertEqual(
			GoogleAuthenticator().authenticate(self.access_token),
		    email)
