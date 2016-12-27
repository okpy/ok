#!/usr/bin/env python3
"""A sample implementation of a console app that uses OK OAuth without needing
a web browser.
"""
import json
import urllib.parse

import requests

CLIENT_ID = 'example-app'
CLIENT_SECRET = 'example-secret'

SERVER = 'http://localhost:5000'
ACCESS_TOKEN_URL = SERVER + '/oauth/token'
AUTHORIZE_URL = SERVER + '/oauth/authorize'
USER_URL = SERVER + '/api/v3/user/'
OAUTH_SCOPE = 'all'
OAUTH_OUT_OF_BAND_URI = 'urn:ietf:wg:oauth:2.0:oob'

if __name__ == '__main__':
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': OAUTH_OUT_OF_BAND_URI,
        'response_type': 'code',
        'scope': OAUTH_SCOPE,
    }
    url = '{}?{}'.format(AUTHORIZE_URL, urllib.parse.urlencode(params))

    print('Paste the following URL into your browser.')
    print()
    print('\t' + url)
    print()
    print('Paste the authorization code below.')
    code = input('Authorization code: ')

    response = requests.post(ACCESS_TOKEN_URL, data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': OAUTH_OUT_OF_BAND_URI,
        'scope': OAUTH_SCOPE,
    })
    response.raise_for_status()
    access_token = response.json()['access_token']

    response = requests.get(USER_URL, params={'access_token': access_token})
    response.raise_for_status()
    print(json.dumps(response.json(), sort_keys=True, indent=4, separators=(',', ': ')))
