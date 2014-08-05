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

    def get_user(self, email, admin=False):
        users = list(models.User.query().filter(email == models.User.email))
        if len(users) == 0:
            role = ADMIN_ROLE if admin else STUDENT_ROLE
            user = models.User(
                email=email,
                role=role
            )
            user.put()
            return user
        return users[0]


class GoogleAuthenticator(Authenticator):

    API_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

    def authenticate(self, access_token):
        response = requests.get(self.API_URL, params={
            'access_token': access_token
        }).json()
        if 'error' in response:
            raise AuthenticationException("access token invalid")
        if 'email' not in response:
            raise AuthenticationException("email doesn't exist")
        return response['email']


class DummyAuthenticator(Authenticator):

    ACCOUNTS = {
        "dummy_student": models.User(
            email="dummy@student.com",
            first_name="Dummy",
            last_name="Jones",
            login="some13413"
        ),
        "dummy_admin": models.User(
            email="dummy@admin.com",
            first_name="Admin",
            last_name="Jones",
            login="albert",
            role=ADMIN_ROLE
        ),
    }

    def authenticate(self, access_token):
        if access_token in self.ACCOUNTS:
            return self.ACCOUNTS[access_token].email
        if access_token == "bad_access_token":
            raise AuthenticationException("access token invalid")
        return "%s@gmail.com" % access_token

    def get_user(self, email):
        return super(DummyAuthenticator, self).get_user(email, "admin" in email)
