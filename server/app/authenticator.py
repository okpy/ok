from app import models
from app.constants import STUDENT_ROLE, ADMIN_ROLE

import requests


class AuthenticationException(Exception):
    pass


class Authenticator(object):

    def __init__(self):
        pass

    def authenticate(self, access_token):
        raise NotImplementedError


class GoogleAuthenticator(Authenticator):

    API_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

    def authenticate(self, access_token):
        return access_token
        response = requests.get(self.API_URL, params={
            'access_token': access_token
        }).json()
        if 'error' in response:
            raise AuthenticationException("access token invalid")
        if 'email' not in response:
            raise AuthenticationException("email doesn't exist")
        return response['email']


