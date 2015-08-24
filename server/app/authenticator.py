import requests


class AuthenticationException(Exception):
    """
    Exception thrown when authentication fails.
    """
    pass


class Authenticator(object):
    """
    Authenticates a user with an access token.
    """

    def __init__(self):
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

    def authenticate(self, access_token):
        response = requests.get(self.API_URL, params={
            'access_token': access_token
        }).json()
        if 'error' in response:
            raise AuthenticationException("access token invalid")
        if 'email' not in response:
            raise AuthenticationException("email doesn't exist")
        return response['email'].lower()


class TestingAuthenticator(Authenticator):
    """
    Authenticates a user with an access token.
    FOR TESTING ONLY.
    """
    def authenticate(self, access_token):
        return access_token


