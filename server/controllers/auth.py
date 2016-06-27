"""
There are two ways to authenticate a request:
* Present the session cookie returned after logging in
* Send a Google access token as the access_token query parameter
"""
from flask import (abort, Blueprint, current_app, flash, redirect,
                   render_template, request, session, url_for)
from flask_oauthlib.client import OAuth, OAuthException
from flask_login import (LoginManager, login_user, logout_user, login_required,
                         current_user)

import logging

from server import utils
from server.models import db, User, Enrollment
from server.extensions import csrf

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
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

@google_auth.tokengetter
def google_oauth_token(token=None):
    return session.get('google_token', None)

def user_from_email(email):
    """Get a User with the given email, or create one."""
    user = User.lookup(email)
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()
    return user

def user_from_access_token(token):
    """
    Get a User with the given Google access token, or create one if no User with
    this email is found. If the token is invalid, return None.
    """
    if use_testing_login() and token == "test":
        return user_from_email("okstaff@okpy.org")
    resp = google_auth.get('userinfo', token=(token, ''))
    if resp.status != 200:
        return None
    return user_from_email(resp.data['email'])

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
    token = request.args.get('access_token', None)
    if token is None:
        return None
    return user_from_access_token(token)

@login_manager.unauthorized_handler
def unauthorized():
    session['after_login'] = request.url
    return redirect(url_for('auth.login'))

def authorize_user(user):
    login_user(user)
    after_login = session.pop('after_login', None)
    return redirect(after_login or url_for('student.index'))

def use_testing_login():
    """
    Return True if we use the unsecure testing login instead of Google OAuth.
    Requires TESTING_LOGIN = True in the config and the environment is not prod.
    """
    return current_app.config.get('TESTING_LOGIN', False) and \
        current_app.config.get('ENV') != 'prod'

@auth.route("/login/")
def login():
    """
    Authenticates a user with an access token using Google APIs.
    """
    return google_auth.authorize(callback=url_for('.authorized', _external=True))

@auth.route('/login/authorized/')
@google_auth.authorized_handler
def authorized(resp):
    if isinstance(resp, OAuthException):
        error = "{0} - {1}".format(resp.data['error'], resp.data['error_description'])
        flash(error, "error")
        # TODO Error Page
        return redirect("/")
    if resp is None:
        error = "Access denied: reason={0} error={1}".format(
            request.args['error_reason'],
            request.args['error_description']
        )
        flash(error, "error")
        # TODO Error Page
        return redirect("/")

    access_token = resp['access_token']
    user = user_from_access_token(access_token)
    session['google_token'] = (access_token, '')  # (access_token, secret)
    return authorize_user(user)


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
    return render_template('testing-login.html',
        callback=url_for(".testing_authorized"),
        random_admin=utils.random_row(User.query.filter_by(is_admin=True)),
        random_staff=random_staff,
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
    session.pop('google_token', None)
    session.pop('sudo-user', None)
    return redirect(url_for('student.index'))

@auth.route("/logout/", methods=['POST'])
@login_required
def logout():
    # Only CSRF protect this route.
    csrf.protect()

    logout_user()
    session.pop('google_token', None)
    session.pop('sudo-user', None)
    return redirect(url_for('student.index'))
