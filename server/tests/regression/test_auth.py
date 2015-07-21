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
		self.real_auth, self.real_user_getorinsert = app.config['AUTHENTICATOR'].authenticate, models.User.get_or_insert
		flask.request = self.flask_request({})
		users.get_current_user = self.get_current_user
		app.config['AUTHENTICATOR'].authenticate, auth.MC_NAMESPACE = self.authenticate, 'test-access-token'
		self.user_email = 'new@special.com'
		
		@staticmethod
		def get_or_insert(email):
			return {'email': email}
		models.User.get_or_insert = get_or_insert

	def tearDown(self):
		""" restore packages """
		flask.request, users.get_current_user = self.real_flaskrequest, self.real_getcurrentuser
		app.config['AUTHENTICATOR'].authenticate, auth.MC_NAMESPACE = self.real_auth, "access-token"
		models.User.get_or_insert = self.real_user_getorinsert
		

	def get_current_user(self):
		return self.user

	def obj(self):
		return lambda: '_'

	def create_user(self, email):
		user = self.obj()
		user.email = lambda: email
		return user

	def flask_request(self, args):
		self.request = request = self.obj()
		request.args = args
		return request

	@staticmethod
	def authenticate(obj):
		return 'new@special.com'

	########
	# TEST #
	########

	def test_authenticated(self):
		""" Tests that an authenticated user is allowed """
		self.user = self.create_user(self.user_email)
		self.assertEqual(auth.authenticate()['email'], self.user.email())

	def test_nonauthenticated_anon(self):
		""" Tests return <anon> when no access token """
		self.user = None
		assert users.get_current_user() is None
		assert 'access_token' not in flask.request.args
		self.assertEqual(auth.authenticate()['email'], '<anon>')

	def test_cached_user(self):
		""" Tests that cached user is returned """
		mc.set(
			"%s-%s" % (MC_NAMESPACE, self.access_token),
			{'email': [self.user_email]})
		self.request.args = {'access_token': self.access_token}
		assert users.get_current_user() is None
		assert 'access_token' in flask.request.args
		self.assertEqual(auth.authenticate()['email'], self.user_email)

	def test_non_cached_non_authenticated_user(self):
		""" Tests that non-cached, non-authenticated user returns _anon """
		self.request.args = {'access_token': self.access_token}
		def authenticate(access_token):
			raise AuthenticationException()
		app.config['AUTHENTICATOR'].authenticate = authenticate
		assert users.get_current_user() is None
		assert 'access_token' in flask.request.args
		assert mc.get("%s-%s" % (MC_NAMESPACE, self.access_token)) is None
		self.assertEqual(auth.authenticate()['email'], '_anon')

	def test_non_cached_authenticated_user(self):
		""" Tests that non-cached but authenticated user returns the user """
		self.request.args = {'access_token': self.access_token}
		assert users.get_current_user() is None
		assert 'access_token' in flask.request.args
		assert mc.get("%s-%s" % (MC_NAMESPACE, self.access_token)) is None
		self.assertEqual(auth.authenticate()['email'], self.user_email)