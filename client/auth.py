#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, './.lib')

import time
import webbrowser
import pdb
from urllib.parse import urlparse, parse_qs
import http.server
import json
from rauth import OAuth2Service
import requests

CLIENT_ID = '479286488889-loj7p7nmvhvbp3ja9tcqlft39sdn1gnq.apps.googleusercontent.com'
CLIENT_SECRET = 'bmMO2-2uO5CpTdw93L19oZ0d'
AUTH_URL = "https://accounts.google.com/o/oauth2/token"
REFRESH_FILE = '.refresh'
TIMEOUT = 10

SUCCESS_HTML ="""
<html>
<head>
<title>Authentication Success</title>
</head>
<body>
<b>You have successfully authenticated into ok.py!</b>
</body>
</html>
"""

def make_code_post(code):
    params = {
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "redirect_uri": "http://localhost:7777",
    }
    r = requests.post(AUTH_URL, data=params)
    result = json.loads(r.text)
    auth_token = result["access_token"]
    refresh_token = result["refresh_token"]
    return auth_token, refresh_token

def make_refresh_post(refresh_token):
    params = {
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
    }
    r = requests.post(AUTH_URL, data=params)
    result = json.loads(r.text)
    if "access_token" not in result:
        raise Exception("refresh token invalid")
    auth_token = result["access_token"]
    return auth_token

def authenticate(force=False):
    """
    Returns an oauth token that can be passed up to the server for identification
    """
    if not force:
        try:
            refresh_file = open(REFRESH_FILE, 'r')
            refresh_token = refresh_file.read()
            auth_token = make_refresh_post(refresh_token)
            return auth_token
        except IOError as error:
            print('Performing authentication')
        except Exception as error:
            print('Performing authentication')

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

    done = False
    access_token = None
    refresh_token = None
    class CodeHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            """Respond to the GET request made by the OAuth"""
            path = urlparse(self.path)
            nonlocal access_token, refresh_token, done
            qs = parse_qs(path.query)
            print(qs)
            code = qs['code'][0]
            access_token, refresh_token = make_code_post(code)

            done = True
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(SUCCESS_HTML, "utf-8"))
            self.wfile.close()

    server_address = ('localhost', 7777)
    httpd = http.server.HTTPServer(server_address, CodeHandler)
    httpd.handle_request()

    fp = open(REFRESH_FILE, 'w')
    fp.write(refresh_token)
    fp.close()
    return access_token

if __name__ == "__main__":
    print(authenticate(force=True))
