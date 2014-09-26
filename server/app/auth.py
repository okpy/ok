"""Convert access tokens to user records."""

# Because pylint doesn't understand memcache for some reason
# pylint: disable=no-member

from app import models
from app import app
from app.authenticator import AuthenticationException

from google.appengine.api import memcache as mc

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
        return models.anonymous
    else:
        access_token = request.args['access_token']
        user = mc.get("%s-%s" % (MC_NAMESPACE, access_token))
        if user:
            return user
        try:
            email = authenticator.authenticate(access_token)
        except AuthenticationException:
            return models.anonymous
        user = models.User.get_or_insert(email)
        mc.set("%s-%s" % (MC_NAMESPACE, access_token), user)
    return user
