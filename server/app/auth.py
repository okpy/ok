"""Convert access tokens to user records."""

from app import models
from app import app
from app.utils import create_api_response
from app.authenticator import AuthenticationException

from flask import request

MC_NAMESPACE = "access-token"

def authenticate():
    """Returns the user which made this request."""
    authenticator = app.config["AUTHENTICATOR"]
    if 'access_token' not in request.args:
        user = models.AnonymousUser
    else:
        access_token = request.args['access_token']

        # TODO(denero) Use memcache to speed up user lookup.
        # See: https://github.com/Cal-CS-61A-Staff/ok/blob/
        #          994144a99881d21f5aefbde8689b388fffa9bd81/server/app/auth.py
        try:
            email = authenticator.authenticate(access_token)
        except AuthenticationException as e:
            return create_api_response(401, e.message)
        user = models.User.get_or_insert(email)
    return user
