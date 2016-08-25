import datetime as dt
import logging

from flask import (abort, Blueprint, current_app, flash, redirect,
                   render_template, request, session, url_for, jsonify)

from flask_login import login_required, current_user, login_user
from flask_oauthlib.contrib.oauth2 import bind_sqlalchemy

from server import utils
from server.models import db, User, Enrollment, Client, Token, Grant
from server.extensions import csrf, oauth_provider

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

@oauth.route('/oauth/authorize', methods=['GET', 'POST'])
@oauth_provider.authorize_handler
@login_required
def authorize(*args, **kwargs):
    if request.method == 'GET':
        client_id = kwargs.get('client_id')
        client = Client.query.filter_by(client_id=client_id).first()
        kwargs['client'] = client
        return render_template('auth/oauthorize.html', **kwargs)

    confirm = request.form.get('confirm', 'no')
    return confirm == 'yes'

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
    error = request.args.get('error', 'Unknown Error')
    description = request.args.get('error_description', 'No details available')
    return render_template('errors/generic.html',
                           error=error, description=description), 400
