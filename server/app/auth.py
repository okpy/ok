from google.appengine.api import memcache

from app import app
from app import models
from app.api import API_PREFIX, create_api_response, handle_error

from flask import request
from functools import wraps
import requests

GOOGLE_API_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

MC_NAMESPACE = "access-token"

def requires_authenticated_user(func):
    """Decorator that determines which user made the request and passes it as a keyword argument"""
    @wraps(func)
    def decorated(*args, **kwargs):
        if 'access_token' not in request.args:
            return create_api_response(401,
                                       "access token required for this method")
        access_token = request.args['access_token']
        mc_key = "%s-%s" % (MC_NAMESPACE, access_token)
        email = memcache.get(mc_key) # pylint: disable=no-member
        if not email:
            response = requests.get(GOOGLE_API_URL, params={
                "access_token": access_token
            }).json()
            if 'error' in response:
                return create_api_response(401,
                                           "invalid access token")
            if 'email' not in response:
                return create_api_response(401,
                                           "email doesn't exist")
            email = response['email']
            memcache.set(mc_key, email, time=60) # pylint: disable=no-member
        users = list(models.User.query().filter(models.User.email == email))
        if len(users) == 0:
            return create_api_response(401, "user with email(%s) doesn't exist"
                                       % email)
        user = users[0]
        return func(*args, user=user, **kwargs)
    return decorated


@app.route("%s/me" % API_PREFIX)
@handle_error
@requires_authenticated_user
def authenticate(user=None):
    return create_api_response(200, "success", user)
