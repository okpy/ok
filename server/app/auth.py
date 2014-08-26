"""Convert access tokens to user records."""

from app import models
from app import app
from app.utils import create_api_response
from app.authenticator import AuthenticationException

from flask import request

from google.appengine.api import users

MC_NAMESPACE = "access-token"

def authenticate():
    """Returns the user which made this request."""
    authenticator = app.config["AUTHENTICATOR"]
    user = users.get_current_user()
    if user:
        return models.User.get_or_insert(user.email())

    if 'access_token' not in request.args:
        return models.AnonymousUser
    else:
        access_token = request.args['access_token']

        # TODO(denero) Use memcache to speed up user lookup.
        # See: https://github.com/Cal-CS-61A-Staff/ok/blob/
        #          994144a99881d21f5aefbde8689b388fffa9bd81/server/app/auth.py
        try:
            email = authenticator.authenticate(access_token)
        except AuthenticationException as e:
            return create_api_response(401, e.message)
        return models.User.get_or_insert(email)
