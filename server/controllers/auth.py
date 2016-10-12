"""
There are two ways to authenticate a request:
* Present the session cookie returned after logging in
* Send a Google access token as the access_token query parameter
"""
from flask import (abort, Blueprint, current_app, flash, redirect,
                   render_template, request, session, url_for, jsonify)
from flask_oauthlib.client import OAuth, OAuthException
from flask_oauthlib.contrib.oauth2 import bind_sqlalchemy

from flask_login import (LoginManager, login_user, logout_user, login_required,
                         current_user)
import requests

import datetime as dt
import logging

from server import utils
from server.models import db, User, Enrollment, Client, Token, Grant
from server.extensions import csrf, oauth_provider, cache

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)

auth.config = {}

@auth.record
def record_params(setup_state):
    """ Load used app configs into local config on registration from
    server/__init__.py """
    app = setup_state.app
    oauth.init_app(app)

oauth = OAuth()
google_auth = oauth.remote_app(
    'google',
    app_key='GOOGLE',
    request_token_params={
        'scope': 'email',
        'prompt': 'select_account'
    },
    base_url='https://www.googleapis.com/oauth2/v3/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

@google_auth.tokengetter
def google_oauth_token(token=None):
    return session.get('google_token')

###########
# Helpers #
###########

def check_oauth_token(scopes=None):
    """ Check the request for OAuth creds.
    Requires: Flask Request and access_token in request.args
    Return Token or None
    """
    if scopes is None:
        scopes = []
    # Check with local OAuth Provider for user
    valid, req = oauth_provider.verify_request(scopes)
    if valid:
        return req

def get_token_if_valid(treshold_min=2):
    """ Get the current google token if it will continue to be valid for the
    next TRESHOLD_MIN minutes. Otherwise, return None.
    """
    future_usage = dt.datetime.now() + dt.timedelta(minutes=treshold_min)
    expiry_time = session.get('token_expiry')
    if expiry_time and expiry_time >= future_usage:
        return session.get('google_token')
    return None

def user_from_email(email):
    """Get a User with the given email, or create one."""
    user = User.lookup(email)
    if not user:
        logger.info("Creating user {}".format(email))
        user = User(email=email)
        db.session.add(user)
        db.session.commit()
    return user

def google_oauth_request(token):
    """ Use fallback of Google Plus Endpoint Profile Info.
    """

@cache.memoize(timeout=600)
def google_user_data(token, timeout=5):
    """ Query google for a user's info. """
    if not token:
        logger.info("Google Token is None")
        return None
    google_plus_endpoint = "https://www.googleapis.com/plus/v1/people/me?access_token={}"

    try:
        r = requests.get(google_plus_endpoint.format(token), timeout=timeout)
        data = r.json()
        if 'error' not in data and data.get('emails'):
            user_email = data['emails'][0]['value']
            return {'email': user_email}
    except requests.exceptions.Timeout as e:
        logger.error("Timed out when using google+")
        return None

    # If Google+ didn't work - fall back to OAuth2
    oauth2_endpoint = "https://www.googleapis.com/oauth2/v3/userinfo?access_token={}"

    try:
        r = requests.get(oauth2_endpoint.format(token), timeout=timeout)
        data = r.json()
        if r.status_code != 200:
            logger.error("Google returned non 200 status code: {}", r.status_code)
        return data
    except requests.exceptions.Timeout as e:
        logger.error("Timed out when using google oauth2")
        return None

    logger.warning("None of the endpoints returned an access token.")
    return None

def user_from_google_token(token):
    """
    Get a User with the given Google access token, or create one if no User with
    this email is found. If the token is invalid, return None.
    """
    if not token:
        return None
    if use_testing_login() and token == "test":
        return user_from_email("okstaff@okpy.org")
    user_data = google_user_data(token)

    if not user_data:
        cache.delete_memoized(google_user_data, token)
        logger.warning("Could not login with oauth. Trying again".format(token))
        user_data = google_user_data(token, timeout=10)

    if not user_data:
        cache.delete_memoized(google_user_data, token)
        logger.warning("Auth Retry failed for token {}".format(token))
        return None

    return user_from_email(user_data['email'])

login_manager = LoginManager()

@login_manager.user_loader
def load_user(userid):
    return User.get_by_id(userid)

@login_manager.request_loader
def load_user_from_request(request):
    """ For the API routes to allow login via access_token.
    """
    if request.blueprint != "api":
        return None
    # Checks for bearer token in header authentication
    oauth_token = check_oauth_token()
    if oauth_token:
        oauth_token.user.scopes = oauth_token.access_token.scopes
        return oauth_token.user
    # Fallback to Google Auth
    token = request.args.get('access_token')
    return user_from_google_token(token)

@login_manager.unauthorized_handler
def unauthorized():
    session['after_login'] = request.url
    return redirect(url_for('auth.login'))

def authorize_user(user):
    if user is None:
        logger.error("Google Auth Failure - attempting to authorize None user")
        raise TypeError("Cannot login as None")
    login_user(user)
    after_login = session.pop('after_login', None)
    return redirect(after_login or url_for('student.index'))

def use_testing_login():
    """
    Return True if we use the unsecure testing login instead of Google OAuth.
    Requires TESTING_LOGIN = True in the config and the environment is not prod.
    """
    return (current_app.config.get('TESTING_LOGIN', False) and
            current_app.config.get('ENV') != 'prod')

def csrf_check():
    """ Manually against CSRF if available. Usually done by default, but this
    function is neccesary for routes in blueprints that have disabled csrf protection.

    CSRF protect is disabled in testing, but not in dev or prod.
    Always checks for CSRF in prod
    """
    current_env = current_app.config.get('ENV')
    csrf_enabled = current_app.config.get('WTF_CSRF_ENABLED', True)

    if current_env == 'prod' or csrf_enabled:
        csrf.protect()

@auth.route("/login/")
def login():
    """
    Authenticates a user with an access token using Google APIs.
    """
    if use_testing_login():
        return redirect(url_for('.testing_login'))
    return google_auth.authorize(callback=url_for('.authorized', _external=True))

@auth.route('/login/authorized/')
def authorized():
    resp = google_auth.authorized_response()
    if resp is None:
        error = "Access denied: reason={0} error={1}".format(
            request.args['error_reason'],
            request.args['error_description']
        )
        flash(error, "error")
        # TODO Error Page
        return redirect("/")
    if isinstance(resp, OAuthException):
        error = "{0} - {1}".format(resp.data.get('error', 'Unknown Error'),
                                   resp.data.get('error_description', 'Unknown'))
        flash(error, "error")
        # TODO Error Page
        return redirect("/")

    access_token = resp['access_token']
    user = user_from_google_token(access_token)
    if not user:
        logger.warning("Attempt to get user info failed")
        flash("We could not log you in. Maybe try another email?", 'warning')
        return redirect("/")

    logger.info("Login from {}".format(user.email))
    expires_in = resp.get('expires_in', 0)
    session['token_expiry'] = dt.datetime.now() + dt.timedelta(seconds=expires_in)
    session['google_token'] = (access_token, '')  # (access_token, secret)
    return authorize_user(user)

################
# Other Routes #
################

@auth.route('/sudo/<email>/')
@login_required
def sudo_login(email):
    logger.info("Sudo attempt to %s from %s", email, current_user)
    if not current_user.is_admin:
        logger.info("Unauthorized sudo %s", current_user)
        return abort(403, 'Unauthorized to sudo')
    user = User.lookup(email)
    if not user:
        return abort(404, "User does not exist")
    logger.info("Sudo Mode: %s from %s", email, current_user)
    session['sudo-user'] = current_user.email
    return authorize_user(user)

# Backdoor log in if you want to impersonate a user.
# Will not give you a Google auth token.
# Requires that TESTING_LOGIN = True in the config and we must not be running in prod.
@auth.route('/testing-login/')
def testing_login():
    if not use_testing_login():
        abort(404)

    random_staff = utils.random_row(Enrollment.query.filter_by(role='staff'))
    if random_staff:
        random_staff = random_staff.user
    random_student = utils.random_row(Enrollment.query.filter_by(role='student'))
    if random_student:
        random_student = random_student.user
    return render_template('testing-login.html',
        callback=url_for(".testing_authorized"),
        random_admin=utils.random_row(User.query.filter_by(is_admin=True)),
        random_staff=random_staff,
        random_student=random_student,
        random_user=utils.random_row(User.query))

@auth.route('/testing-login/authorized/', methods=['POST'])
def testing_authorized():
    if not use_testing_login():
        abort(404)
    user = user_from_email(request.form['email'])
    return authorize_user(user)

@auth.route('/testing-login/logout/', methods=['POST'])
def testing_logout():
    if not use_testing_login():
        abort(404)
    logout_user()
    session.clear()
    return redirect(url_for('student.index'))

@auth.route("/logout/", methods=['POST'])
@login_required
def logout():
    # Only CSRF protect this route.
    csrf_check()

    logout_user()
    session.clear()
    return redirect(url_for('student.index'))
