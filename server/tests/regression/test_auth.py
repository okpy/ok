from test_base import auth, BaseTestCase, models

from google.appengine.api import users, memcache as mc
from app import app, auth
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
	user_email = 'new@special.com'
	MC_NAMESPACE = 'test-access-token'

	def setUp(self):
		super(AuthTestCase, self).setUp()
		self.user = None
		self.mock(flask, 'request').using(self.flask_request({}).request)
		self.mock(users, 'get_current_user').using(self.get_current_user)
		self.mock(app.config['AUTHENTICATOR'], 'authenticate').using(self.authenticate)
		self.mock(models.User, 'get_or_insert').using(staticmethod(lambda email: {'email': email}))
		self.mock(auth, 'MC_NAMESPACE').using(AuthTestCase.MC_NAMESPACE)

	def get_current_user(self):
		return self.user

	def flask_request(self, args):
		self.request = self.obj().set(args=args)
		return self

	@staticmethod
	def authenticate(obj):
		return 'new@special.com'

	########
	# TEST #
	########

	def test_authenticated(self):
		""" Tests that an authenticated user is allowed """
		self.user = self.obj().set(email=lambda: self.user_email)
		self.assertEqual(auth.authenticate()['email'], self.user.email())

	def test_nonauthenticated_anon(self):
		""" Tests return <anon> when no access token """
		AuthTestCase.user = None
		assert users.get_current_user() is None
		assert 'access_token' not in flask.request.args
		self.assertEqual(auth.authenticate()['email'], '<anon>')

	def test_cached_user(self):
		""" Tests that cached user is returned """
		mc.set(
			"%s-%s" % (AuthTestCase.MC_NAMESPACE, self.access_token),
			{'email': [self.user_email]})
		self.request.args = {'access_token': self.access_token}
		assert users.get_current_user() is None
		assert 'access_token' in flask.request.args
		assert mc.get('%s-%s' % (AuthTestCase.MC_NAMESPACE, self.access_token))
		self.assertEqual(auth.authenticate()['email'][0], self.user_email)

	def test_non_cached_non_authenticated_user(self):
		""" Tests that non-cached, non-authenticated user returns _anon """
		self.request.args = {'access_token': self.access_token}
		def authenticate(access_token):
			raise AuthenticationException()
		app.config['AUTHENTICATOR'].authenticate = authenticate
		assert users.get_current_user() is None
		assert 'access_token' in flask.request.args
		assert mc.get("%s-%s" % (AuthTestCase.MC_NAMESPACE, self.access_token)) is None
		self.assertEqual(auth.authenticate()['email'], '_anon')

	def test_non_cached_authenticated_user(self):
		""" Tests that non-cached but authenticated user returns the user """
		self.request.args = {'access_token': self.access_token}
		assert users.get_current_user() is None
		assert 'access_token' in flask.request.args
		assert mc.get("%s-%s" % (AuthTestCase.MC_NAMESPACE, self.access_token)) is None
		self.assertEqual(auth.authenticate()['email'], self.user_email)
