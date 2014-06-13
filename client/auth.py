#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, './.lib/')

import time
import webbrowser
import pdb
from urllib.parse import urlparse, parse_qs
import http.server
import json

from sanction import Client, transport_headers

CLIENT_ID = '268270530197-0ulshcio7meobp6cdpje1a31ouhrcfde.apps.googleusercontent.com'
CLIENT_SECRET = 'nbCCdqiKOFvJaSrTCmjtjGMe'
REFRESH_FILE = '.refresh'
REDIRECT_URI = "http://localhost:7777/"
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
    client = Client(token_endpoint='https://accounts.google.com/o/oauth2/token',
                    resource_endpoint='https://www.googleapis.com/oauth2/v1',
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET
                    )
    params = {
        "redirect_uri": REDIRECT_URI
    }
    client.request_token(code=code, **params)
    return client.access_token, client.refresh_token

def make_refresh_post(refresh_token):
    client = Client(token_endpoint='https://accounts.google.com/o/oauth2/token',
                    resource_endpoint='https://www.googleapis.com/oauth2/v1',
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET
                    )
    params = {
        "grant_type": "refresh_token"
    }
    client.request_token(refresh_token=refresh_token, **params)
    return client.access_token

def authenticate(force=False):
    """
    Returns an oauth token that can be passed up to the server for identification
    """
    if not force:
        try:
            with open(REFRESH_FILE) as refresh_file:
                refresh_token = refresh_file.read()
            auth_token = make_refresh_post(refresh_token)
            return auth_token
        except IOError as error:
            print('Performing authentication')
        except Exception as error:
            print('Performing authentication')

    c = Client(auth_endpoint='https://accounts.google.com/o/oauth2/auth',
               client_id=CLIENT_ID)
    url = c.auth_uri(scope="profile email", access_type='offline', name='okpy-ucb',
                     redirect_uri=REDIRECT_URI)

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
            code = qs['code'][0]
            access_token, refresh_token = make_code_post(code)

            done = True
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(SUCCESS_HTML, "utf-8"))

    server_address = ('localhost', 7777)
    httpd = http.server.HTTPServer(server_address, CodeHandler)
    httpd.handle_request()

    with open(REFRESH_FILE, 'w') as fp:
        fp.write(refresh_token)

    return access_token

if __name__ == "__main__":
    print(authenticate())
