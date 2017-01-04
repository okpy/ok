import datetime as dt
import functools
import logging
import urllib.parse

from flask import (Blueprint, flash, redirect, render_template,
                   request, session, url_for, jsonify, make_response)

from flask_login import current_user, login_required, logout_user

from server.constants import OAUTH_OUT_OF_BAND_URI
from server.models import db, Client, Token, Grant
from server.extensions import csrf, oauth_provider
from server.controllers.auth import csrf_check

logger = logging.getLogger(__name__)

oauth = Blueprint('oauth', __name__)

@oauth.record
def record_params(setup_state):
    """ Load used app configs into local config on registration from
    server/__init__.py """
    app = setup_state.app
    oauth_provider.init_app(app)

@oauth_provider.clientgetter
def load_client(client_id):
    return Client.query.filter_by(client_id=client_id).first()

@oauth_provider.grantgetter
def load_grant(client_id, code):
    return Grant.query.filter_by(client_id=client_id, code=code).first()

@oauth_provider.grantsetter
def save_grant(client_id, code, request, *args, **kwargs):
    expires = dt.datetime.utcnow() + dt.timedelta(seconds=100)
    grant = Grant(
        client_id=client_id,
        code=code['code'],
        redirect_uri=request.redirect_uri,
        scopes=request.scopes,
        user=current_user,
        expires=expires
    )
    db.session.add(grant)
    db.session.commit()
    return grant

@oauth_provider.tokengetter
def load_token(access_token=None, refresh_token=None):
    if access_token:
        return Token.query.filter_by(access_token=access_token).first()
    elif refresh_token:
        return Token.query.filter_by(refresh_token=refresh_token).first()

@oauth_provider.tokensetter
def save_token(token, orequest, *args, **kwargs):
    toks = Token.query.filter_by(client_id=orequest.client.client_id,
                                 user_id=orequest.user.id).all()
    # make sure that every client has only one token connected to a user
    for t in toks:
        db.session.delete(t)

    expires_in = token.get('expires_in')
    expires = dt.datetime.utcnow() + dt.timedelta(seconds=expires_in)

    tok = Token(
        access_token=token['access_token'],
        refresh_token=token['refresh_token'],
        token_type=token['token_type'],
        scopes=token['scope'].split(),
        expires=expires,
        client_id=orequest.client.client_id,
        user_id=orequest.user.id,
    )
    db.session.add(tok)
    db.session.commit()
    return tok

def intercept_out_of_band_redirect(f):
    """Wraps the authorize route below. If it returns a redirect to
    OAUTH_OUT_OF_BAND_URI, display the code or errors in the browser instead
    of redirecting to the client.
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        response = make_response(f(*args, **kwargs))
        if response.status_code == 302:
            o = urllib.parse.urlparse(response.headers['Location'])
            if o.scheme + ':' + o.path == OAUTH_OUT_OF_BAND_URI:
                query = {k: v for k, v in urllib.parse.parse_qsl(o.query)}
                code = query.get('code')
                if code:
                    client_id = request.form.get('client_id')
                    return redirect(url_for('.oauth_code', client_id=client_id, code=code))
                else:
                    return redirect(url_for('.oauth_errors', **query))
        return response
    return wrapper

@oauth.route('/oauth/authorize', methods=['GET', 'POST'])
@login_required
@intercept_out_of_band_redirect
@oauth_provider.authorize_handler
def authorize(*args, **kwargs):
    # Only CSRF protect this route.
    csrf_check()

    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        kwargs['client'] = client
        return render_template('auth/oauthorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'

@oauth.route('/oauth/code')
def oauth_code():
    client_id = request.args.get('client_id')
    client = Client.query.filter_by(client_id=client_id).first()
    code = request.args.get('code')
    return render_template('auth/code.html', client=client, code=code)

@oauth.route('/oauth/reauthenticate')
def reauthenticate():
    logout_user()
    session.clear()
    return redirect(url_for('.authorize', **request.args))

@oauth.route('/oauth/token', methods=['POST'])
@oauth_provider.token_handler
def access_token():
    """ Exchange/Refresh the token. Flask-OAuthLib handles this. """
    return None

@oauth.route('/oauth/revoke', methods=['POST'])
@oauth_provider.revoke_handler
def revoke_token():
    return

@oauth.route('/oauth/errors')
def oauth_errors():
    error = request.args.get('error')
    if error:
        # 'access_denied' -> 'Access Denied'
        error = error.replace('_', ' ').title()
    description = request.args.get('error_description')
    return render_template('errors/generic.html',
                           error=error, description=description), 400

@oauth.route('/client/login/')
def client_login():
    return redirect(url_for('.authorize',
        client_id='ok-client',
        redirect_uri=OAUTH_OUT_OF_BAND_URI,
        response_type='code',
        scope='all'))
