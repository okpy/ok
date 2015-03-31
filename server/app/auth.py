"""Convert access tokens to user records."""

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
        return models.User.get_or_insert(user.email().lower())

    if 'access_token' not in request.args:
        print 'ANON user'
        return models.User.get_or_insert("<anon>")
    else:
        access_token = request.args['access_token']
        print 'USING ACCESS TOKEN', access_token
        user = mc.get("%s-%s" % (MC_NAMESPACE, access_token))
        if user:
            return user
        try:
            email = authenticator.authenticate(access_token)
        except AuthenticationException:
            return models.User.get_or_insert('_anon')
        user = models.User.get_or_insert(email)
        mc.set("%s-%s" % (MC_NAMESPACE, access_token), user)
    return user
