from flask import abort, Blueprint, current_app, flash, redirect, \
    render_template, request, session, url_for
from flask_oauthlib.client import OAuth
from flask.ext.login import login_user, logout_user, login_required

from server.models import User, db
from server.secret_keys import google_creds

auth = Blueprint('auth', __name__)

oauth = OAuth()
google_auth = oauth.remote_app(
    'google',
    consumer_key=google_creds['GOOGLE_ID'],
    consumer_secret=google_creds['GOOGLE_SECRET'],
    request_token_params={
        'scope': 'email'
    },
    base_url='https://www.googleapis.com/oauth2/v1/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
)

@google_auth.tokengetter
def google_oauth_token():
    return session.get('google_token')

def authorize_user(email, name):
    """
    Logs in a user with the specified email and name and redirects to the home page.
    A User will be created if no User with this email is found.
    """
    user = User.query.filter_by(email=email).first()
    if not user:
        user = User(email, name)
        db.session.add(user)
        db.session.commit()
    flash("Logged in successfully.", "success")
    login_user(user)
    return redirect(request.args.get("next") or url_for("main.home"))

@auth.route("/login")
def login():
    """
    Authenticates a user with an access token using Google APIs.
    """
    if current_app.config.get('TESTING_LOGIN', False):
        return redirect(url_for('.testing_login'))
    return google_auth.authorize(callback=url_for('.authorized', _external=True))

@auth.route('/login/authorized')
def authorized():
    resp = google_auth.authorized_response()
    if resp is None or 'access_token' not in resp:
        error = 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
        flash(error, "error")
        # TODO Error Page
        return redirect(url_for("main.home"))

    session['google_token'] = (resp['access_token'], '')
    me = google_auth.get('userinfo')
    # TODO me.data['name'] is empty for me (knrafto@berkeley.edu)
    return authorize_user(me.data['email'], me.data['name'])

# Backdoor log in if you want to impersonate a user.
# Will not give you a Google auth token.
# Requires that TESTING_LOGIN = True in the config; production should NEVER have this on.
@auth.route('/testing-login')
def testing_login():
    if not current_app.config.get('TESTING_LOGIN', False):
        abort(404)
    return render_template('testing-login.html', callback=url_for(".testing_authorized"))

@auth.route('/testing-login/authorized', methods=['POST'])
def testing_authorized():
    if not current_app.config.get('TESTING_LOGIN', False):
        abort(404)
    session['google_token'] = ('fake', '')
    return authorize_user(request.form['email'], '')

@auth.route("/logout")
def logout():
    logout_user()
    session.pop('google_token', None)
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))

@auth.route("/restricted")
@login_required
def restricted():
    return "You can only see this if you are logged in!", 200
