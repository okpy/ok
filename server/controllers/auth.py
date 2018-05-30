"""
There are two ways to authenticate a request:
* Present the session cookie returned after logging in
* Send an access token as the access_token query parameter to the chosen service provider
"""
import jwt

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
from server.constants import GOOGLE, MICROSOFT

logger = logging.getLogger(__name__)

auth = Blueprint('auth', __name__)

auth.config = {}

provider_auth = None
provider_name = None

oauth = None

@auth.record
def record_params(setup_state):
    """ Load used app configs into local config on registration from
    server/__init__.py """
    global provider_name
    global provider_auth
    global oauth
    oauth = OAuth()
    app = setup_state.app
    provider_name = app.config.get('OAUTH_PROVIDER', GOOGLE)
    provider_auth = oauth.remote_app(
        provider_name, 
        app_key=provider_name
    )
    
    oauth.init_app(app)
    #instead of decorator set the fn pointer to the func here:
    provider_auth._tokengetter = provider_token
   
def provider_token(token=None):
    return session.get('provider_token')

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

    google_plus_endpoint = current_app.config.get(provider_name)['profile_url']

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
    oauth2_endpoint = current_app.config.get(provider_name)['userinfo_url'] 

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

def microsoft_user_data(token):
    """ Query Microsoft for a user's info. """
    if not token:
        logger.info("Microsoft Token is None")
        return None

    try:
        decoded_token = jwt.decode(token, verify=False)
        if 'unique_name' in decoded_token: # azure ad unique id
            logger.info("token found in Azure unique_name value")
            return {'email': decoded_token['unique_name']} 
        if 'upn' in decoded_token:  # fallback to upn
            logger.info("token found in Azure upn value")
            return {'email': decoded_token['upn']}

        # reading from the Token didn't work - now we try a MS Graph Call.
        logger.warning("token had no values and MS Graph WILL be called")
        headers = {'Accept': 'application/json',
                    'Authorization': 'Bearer ' + token}
        r = requests.get(current_app.config.get(provider_name)['base_url'] + '/me', headers=headers)
        ms_graph_me = r.json()
        if 'userPrincipalName' in ms_graph_me:
            logger.warning("token had no values and MS Graph call made!")
            return { 'email': ms_graph_me['userPrincipalName']}

        logger.error("Unable to retrieve unique_name (the user's email) from token")
        return None
    except jwt.DecodeError as e:
        logger.error("jwt decode error from token")
        logger.error('Decode error was %s', e)
        return None

def user_from_provider_token(token):
    """
    Get a User with the given access token, or create one if no User with
    this email is found. If the token is invalid, return None.
    """
    if not token:
        return None
    if use_testing_login() and token == "test":
        return user_from_email("okstaff@okpy.org")

    if provider_name == GOOGLE:
        user_data = google_user_data(token)
    elif provider_name == MICROSOFT:
        user_data = microsoft_user_data(token)

    if not user_data or 'email' not in user_data:
        if provider_name == GOOGLE:
            cache.delete_memoized(google_user_data, token)
        elif provider_name == MICROSOFT:
            cache.delete_memoized(microsoft_user_data, token)

        logger.warning("Auth Retry failed for token {} - {}".format(token, user_data))
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

@login_manager.unauthorized_handler
def unauthorized():
    session['after_login'] = request.url
    login_hint = request.args.get('login_hint')
    return redirect(url_for('auth.login', login_hint=login_hint))

def authorize_user(user):
    if user is None:
        logger.error("Auth Failure - attempting to authorize None user")
        raise TypeError("Cannot login as None")
    login_user(user)
    after_login = session.pop('after_login', None)
    return redirect(after_login or url_for('student.index'))

def use_testing_login():
    """
    Return True if we use the unsecure testing login instead of service provider OAuth.
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
    Authenticates a user with an access token using service provider APIs.
    """
    if use_testing_login():
        return redirect(url_for('.testing_login'))
    return provider_auth.authorize(
        callback=url_for('.authorized', _external=True),
        login_hint=request.args.get('login_hint'))

@auth.route('/login/authorized/')
def authorized():
    resp = provider_auth.authorized_response()
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
    user = user_from_provider_token(access_token)
    if not user:
        logger.warning("Attempt to get user info failed")
        flash("We could not log you in. Maybe try another email?", 'warning')
        return redirect("/")

    logger.info("Login from {}".format(user.email))
    expires_in = utils.safe_cast(resp.get('expires_in'), int, 0)
    session['token_expiry'] = dt.datetime.now() + dt.timedelta(seconds=expires_in)
    session['provider_token'] = (access_token, '')  # (access_token, secret)
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
# Will not give you a service provider auth token.
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
