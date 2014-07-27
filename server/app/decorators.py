"""
Decorators for URL handlers
"""

from functools import wraps
from google.appengine.api import users
from flask import redirect, request, abort


def login_required(func):
    """Requires standard login credentials."""
    @wraps(func)
    def decorated(*args, **kwargs):
        if not users.get_current_user():
            return redirect(users.create_login_url(request.url))
        return func(*args, **kwargs)
    decorated.login_required = True
    return decorated


def admin_required(func):
    """Requires App Engine admin credentials."""
    @wraps(func)
    def decorated(*args, **kwargs):
        if users.get_current_user():
            if not users.is_current_user_admin():
                abort(401)  # Unauthorized
            return func(*args, **kwargs)
        return redirect(users.create_login_url(request.url))
    decorated.login_required = True
    decorated.admin_required = True
    return decorated

