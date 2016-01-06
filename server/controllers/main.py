from flask import Blueprint, render_template, flash, request, redirect, \
    url_for, session,  current_app
from flask.ext.login import login_user, logout_user, login_required

from server.extensions import cache
from server.models import User, db
from server.authenticators import GoogleAuthenticator, TestingAuthenticator

main = Blueprint('main', __name__)

# TODO : Cleanup hacky authenticator chooser. 
google_auth = GoogleAuthenticator(main)
dev_auth = TestingAuthenticator(main)

def choose_auth():
    if current_app.config['AUTH'] == TestingAuthenticator:
        return dev_auth
    return google_auth

@main.route('/')
@cache.cached(timeout=1000)
def home():
    return render_template('index.html')

# TODO : Add testing auth mode, cleanup google attr
@main.route("/login")
def login():
    authenticator = choose_auth()
    return authenticator.authorize(callback=url_for('.authorized', _external=True))

@main.route("/logout")
def logout():
    logout_user()
    session.pop('google_token')
    flash("You have been logged out.", "success")
    return redirect(url_for(".home"))


@main.route('/login/authorized')
def authorized():
    authenticator = choose_auth()
    resp = authenticator.response()
    if resp is None or 'access_token' not in resp:
        error = 'Access denied: reason=%s error=%s' % (
            request.args['error_reason'],
            request.args['error_description']
        )
        flash(error, "error")
        # TODO Error Page
        return redirect(url_for(".home"))

    session['google_token'] = (resp['access_token'], '')
    me = authenticator.get('userinfo')
    email, name = me.data['email'], me.data['name']
    user = User.query.filter_by(email=email).first()
    if user:
        flash("Logged in successfully.", "success")
        login_user(user)
        return redirect(request.args.get("next") or url_for(".home"))
    else:
        new_user = User(email, name)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
    return redirect(url_for(".home"))

@google_auth.google.tokengetter
def get_google_oauth_token():
    return session.get('google_token')



@main.route("/restricted")
@login_required
def restricted():
    return "You can only see this if you are logged in!", 200
