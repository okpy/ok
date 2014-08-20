from google.appengine.api import memcache

from app import models
from app import app
from app.constants import API_PREFIX, ADMIN_ROLE, STUDENT_ROLE
from app.utils import create_api_response
from app.decorators import handle_error
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

        # For now, no memcache usage, so it can be simpler.
        try:
            email = authenticator.authenticate(access_token)
        except AuthenticationException as e:
            return create_api_response(401, e.message)
        user = models.User.get_or_insert(email)
    return user
