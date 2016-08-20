""" This file is a sample implementation of OAuth with OK """
import urllib.parse

from flask import Flask, redirect, url_for, session, request, jsonify, abort
from flask_oauthlib.client import OAuth
import requests

def create_client(app):
    oauth = OAuth(app)

    remote = oauth.remote_app(
        'dev',  # Client Name
        consumer_key='normal',
        consumer_secret='normal',
        request_token_params={'scope': 'all'},
        base_url='http://localhost:5000/api/v3/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='http://localhost:5000/oauth/token',
        authorize_url='http://localhost:5000/oauth/authorize'
    )

    # def check_req(uri, headers, body):
    #     """ Add access_token to the URL Request. """
    #     if 'access_token' not in uri and session.get('dev_token'):
    #         params = {'access_token': session.get('dev_token')[0]}
    #         url_parts = list(urllib.parse.urlparse(uri))
    #         query = dict(urllib.parse.parse_qsl(url_parts[4]))
    #         query.update(params)
    #
    #         url_parts[4] = urllib.parse.urlencode(query)
    #         uri = urllib.parse.urlunparse(url_parts)
    #     return uri, headers, body
    # remote.pre_request = check_req

    @app.route('/')
    def index():
        if 'dev_token' in session:
            ret = remote.get('user', token=session['dev_token'])
            return jsonify(ret.data)
            return "Welcome {}".format(ret.data['data']['email'])
        return redirect(url_for('login'))

    @app.route('/login')
    def login():
        return remote.authorize(callback=url_for('authorized', _external=True))

    @app.route('/logout')
    def logout():
        session.pop('dev_token', None)
        return redirect(url_for('index'))

    @app.route('/authorized')
    def authorized():
        resp = remote.authorized_response()
        if resp is None:
            return 'Access denied: error=%s' % (
                request.args['error']
            )
        if isinstance(resp, dict) and 'access_token' in resp:
            session['dev_token'] = (resp['access_token'], '')
            return jsonify(resp)
        return str(resp)

    @app.route('/user')
    def client_method():
        token = session['dev_token'][0]
        r = requests.get('http://localhost:5000/api/v3/user/?access_token={}'.format(token))
        r.raise_for_status()
        return jsonify(r.json())

    @remote.tokengetter
    def get_oauth_token():
        return session.get('dev_token')

    return remote

if __name__ == '__main__':
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = 'true'
    # DEBUG=1 python oauth2_client.py
    app = Flask(__name__)
    app.debug = True
    app.secret_key = 'development'
    create_client(app)
    app.run(host='127.0.0.1', port=8000)
