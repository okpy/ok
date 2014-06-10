#!/usr/bin/env python3

import os
import sys
import webbrowser
import pdb
from urllib.parse import urlparse, parse_qs
import http.server
import json

sys.path.append(os.path.abspath('./lib'))

from rauth import OAuth2Service
import requests

CLIENT_ID = '479286488889-loj7p7nmvhvbp3ja9tcqlft39sdn1gnq.apps.googleusercontent.com'
CLIENT_SECRET = 'bmMO2-2uO5CpTdw93L19oZ0d'

if __name__ == "__main__":
    google = OAuth2Service(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        access_token_url='https://accounts.google.com/o/oauth2/token',
        base_url='https://accounts.google.com/o/oauth2/auth',
        name='test-project')

    redirect_uri = 'http://localhost:7777'
    params = {
                'scope': 'profile email',
                'response_type': 'code',
                'redirect_uri': redirect_uri,
                'access_type': 'offline'
             }

    url = google.get_authorize_url(**params)
    webbrowser.open(url)


    HOST_NAME = 'localhost'
    PORT_NUMBER = 7777

    code = None
    class CodeHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            """Respond to a GET request."""
            path = urlparse(self.path)
            global code
            code = parse_qs(path.query)['code'][0]
            self.send_response(200)


    server_address = ('', 7777)
    httpd = http.server.HTTPServer(server_address, CodeHandler)
    while not code:
        httpd.handle_request()

    AUTH_URL = "https://accounts.google.com/o/oauth2/token"
    params = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    }
    r = requests.post(AUTH_URL, data=params)
    result = json.loads(r.text)
    auth_token = result["access_token"]
    r = requests.get("https://www.googleapis.com/oauth2/v1/userinfo?access_token=%s" % auth_token)
    user_info = json.loads(r.text)

    print(user_info)
    print(user_info["given_name"], user_info["family_name"])
    print(user_info["email"])

