from flask_oauthlib.client import OAuth
from server.settings import google_creds

import requests


def token_email(access_token):
    response = requests.get(GoogleAuthenticator.API_URL, params={
        'access_token': access_token
    }).json()
    if 'error' in response:
        raise AuthenticationException("access token invalid")
    if 'email' not in response:
        raise AuthenticationException("email doesn't exist")
    return response['email'].lower()


class AuthenticationException(Exception):
    """
    Exception thrown when authentication fails.
    """
    pass


class Authenticator(object):
    """
    Authenticates a user with an access token.
    """

    def __init__(self, app):
        pass

    def authenticate(self, access_token):
        """
        Returns the email this access token corresponds to.
        """
        raise NotImplementedError


class GoogleAuthenticator(Authenticator):
    """
    Authenticates a user with an access token using Google APIs.
    """

    API_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

    def __init__(self, app):
        self.oauth = OAuth(app)
        self.google = self.oauth.remote_app(
            'google',
            consumer_key=google_creds['GOOGLE_ID'],
            consumer_secret=google_creds['GOOGLE_SECRET'],
            request_token_params={
                'scope': 'email'
            },
            base_url='https://www.googleapis.com/oauth2/v1/',
            request_token_url=None,
            access_token_method='POST',
            access_token_url='https://accounts.google.com/o/oauth2/token',
            authorize_url='https://accounts.google.com/o/oauth2/auth',
        )

    def authorize(self, callback):
        return self.google(callback=callback)

    def response(self):
        return self.google.authorized_response()

    def get(self, *args, **kwargs):
        return self.google.get(*args, **kwargs)

    def email(self, access_token):
        return token_email(access_token)


class TestingAuthenticator(Authenticator):
    """
    Authenticates a user with an access token.
    FOR TESTING ONLY.
    """

    def authenticate(self, callback):
        return callback

    def response(self):
        return {'email': 'test@example.com', 'access_token': 'fake'}

    def get(self, *args, **kwargs):
        return self.response()

    def email(self, access_token):
        return access_token
