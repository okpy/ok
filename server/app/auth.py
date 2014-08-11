from google.appengine.api import memcache

from app import models
from app import app
from app.constants import API_PREFIX, ADMIN_ROLE, STUDENT_ROLE
from app.utils import create_api_response
from app.decorators import handle_error
from app.authenticator import AuthenticationException

from flask import request
from functools import wraps


MC_NAMESPACE = "access-token"


def requires_authenticated_user(admin=False, required=False):
    """Decorator that determines which user made the request
    and passes it to the decorated function. The wrapped function
    is called with keyword arg called 'user' that is a user object."""
    def requires_user_with_privileges(func):
        """Higher order function that takes into account admin permissions"""
        @wraps(func)
        def decorated(*args, **kwargs):  #pylint: disable=too-many-return-statements
            authenticator = app.config["AUTHENTICATOR"]
            if 'access_token' not in request.args:
                if required:
                    return create_api_response(401,
                                               "access token required "
                                               "for this method")
                else:
                    user = None
            else:
                access_token = request.args['access_token']
                mc_key = "%s-%s" % (MC_NAMESPACE, access_token)
                email = memcache.get(mc_key) # pylint: disable=no-member
                if not email:
                    try:
                        email = authenticator.authenticate(access_token)
                    except AuthenticationException as e:
                        return create_api_response(401, e.message)
                    memcache.set(mc_key, email,  # pylint: disable=no-member
                                 time=60)
                try:
                    user = models.User.get_or_insert(email,
                            role=(ADMIN_ROLE if admin else STUDENT_ROLE))
                except AuthenticationException as e:
                    return create_api_response(401, e.message)
            if admin and (not user or (user.role != ADMIN_ROLE)):
                return create_api_response(401,
                                           "user lacks permission for this request")

            return func(*args, user=user, **kwargs)
        return decorated
    return requires_user_with_privileges


@app.route("%s/me" % API_PREFIX)
@handle_error
@requires_authenticated_user
def authenticate(user=None):
    return create_api_response(200, "success", user)
