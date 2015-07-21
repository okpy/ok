from test_base import auth, BaseTestCase, models

from google.appengine.api import users, memcache as mc
from app import app, auth
from app.auth import MC_NAMESPACE
import flask
from app.authenticator import AuthenticationException


class AuthTestCase(BaseTestCase):
	"""
	Testing authentication
	"""
	
	#########
	# SETUP #
	#########
	
	access_token = 'gibberish'

	def setUp(self):
		super(AuthTestCase, self).setUp()
		self.setUpImports()

	def setUpImports(self):
		self.user = None
		self.real_flaskrequest, self.real_getcurrentuser = flask.request, users.get_current_user
		flask.request = self.request({})
		users.get_current_user = self.get_current_user
		app.config['AUTHENTICATOR'].authenticate = self.authenticate

	def tearDown(self):
		""" restore packages """
		flask.request, users.get_current_user = self.real_flaskrequest, self.real_getcurrentuser

	def get_current_user(self):
		return self.user

	def obj(self):
		return lambda: '_'

	def create_user(self, email):
		user = self.obj()
		user.email = lambda: email
		return user

	def nonexistent_user(self):
		return self.create_user('test@example.com')

	def registered_user(self):
		return self.create_user('dummy@admin.com')

	def request(self, args):
		request = self.obj()
		request.args = args
		return request

	@staticmethod
	def authenticate(self):
		return 'dummy@admin.com'

	########
	# TEST #
	########

	def test_authenticated(self):
		""" Tests that an authenticated user is allowed """
		self.user = self.registered_user()
		self.assertEqual(auth.authenticate().email[0], self.user.email())

	def test_nonauthenticated_anon(self):
		""" Tests return <anon> when no access token """
		self.user = None
		assert users.get_current_user() is None
		assert 'access_token' not in flask.request.args
		self.assertEqual(auth.authenticate().email[0], '<anon>')

	def test_cached_user(self):
		""" Tests that cached user is returned """
		mc.set(
			"%s-%s" % (MC_NAMESPACE, self.access_token),
			{'email': ['dummy@admin.com']})
		flask.request = self.request({'access_token': self.access_token})
		assert users.get_current_user() is None
		assert 'access_token' in flask.request.args
		self.assertEqual(auth.authenticate()['email'][0], 'dummy@admin.com')

	def test_non_cached_non_authenticated_user(self):
		""" Tests that non-cached, non-authenticated user returns _anon """
		flask.request = self.request({'access_token': self.access_token})
		def authenticate(access_token):
			raise AuthenticationException()
		app.config['AUTHENTICATOR'].authenticate = authenticate
		assert users.get_current_user() is None
		assert 'access_token' in flask.request.args
		assert mc.get("%s-%s" % (MC_NAMESPACE, self.access_token)) is None
		self.assertEqual(auth.authenticate().email[0], '_anon')

	def test_non_cached_authenticated_user(self):
		""" Tests that non-cached but authenticated user returns the user """
		flask.request = self.request({'access_token': self.access_token})
		assert users.get_current_user() is None
		assert 'access_token' in flask.request.args
		assert mc.get("%s-%s" % (MC_NAMESPACE, self.access_token)) is None
		self.assertEqual(auth.authenticate().email[0], 'dummy@admin.com')