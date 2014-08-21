#!/usr/bin/env python3
import sys
sys.path.insert(0, './.lib/sanction.zip')

from sanction import Client

import http.server
from urllib.parse import urlparse, parse_qs
import webbrowser

CLIENT_ID = \
    '931757735585-vb3p8g53a442iktc4nkv5q8cbjrtuonv.apps.googleusercontent.com'
# The client secret in an installed application isn't a secret.
# See: https://developers.google.com/accounts/docs/OAuth2InstalledApp
CLIENT_SECRET = 'zGY9okExIBnompFTWcBmOZo4'
REFRESH_FILE = '.refresh'
REDIRECT_HOST = "localhost"
REDIRECT_PORT = 7777
REDIRECT_URI = "http://%s:%u/" % (REDIRECT_HOST, REDIRECT_PORT)
TIMEOUT = 10

SUCCESS_HTML = """
<html>
<head>
<title>Authentication Success</title>
</head>
<body>
<b>You have successfully authenticated into ok.py!</b>
</body>
</html>
"""

def _make_code_post(code):
    client = Client(
        token_endpoint='https://accounts.google.com/o/oauth2/token',
        resource_endpoint='https://www.googleapis.com/oauth2/v1',
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    params = {"redirect_uri": REDIRECT_URI}
    client.request_token(code=code, **params)
    return client.access_token, client.refresh_token

def make_refresh_post(refresh_token):
    client = Client(
        token_endpoint='https://accounts.google.com/o/oauth2/token',
        resource_endpoint='https://www.googleapis.com/oauth2/v1',
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET)
    params = {"grant_type": "refresh_token"}
    client.request_token(refresh_token=refresh_token, **params)
    return client.access_token

def authenticate(force=False):
    """
    Returns an oauth token that can be passed to the server for identification.
    """
    if not force:
        try:
            with open(REFRESH_FILE) as refresh_file:
                refresh_token = refresh_file.read()
            auth_token = make_refresh_post(refresh_token)
            return auth_token
        except IOError as _:
            print('Performing authentication')
        except Exception as _:
            print('Performing authentication')

    c = Client(auth_endpoint='https://accounts.google.com/o/oauth2/auth',
               client_id=CLIENT_ID)
    url = c.auth_uri(scope="profile email", access_type='offline',
                     name='ok-server', redirect_uri=REDIRECT_URI)

    webbrowser.open(url)

    host_name = REDIRECT_HOST
    port_number = REDIRECT_PORT

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
            access_token, refresh_token = _make_code_post(code)

            done = True
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes(SUCCESS_HTML, "utf-8"))

    server_address = (host_name, port_number)
    httpd = http.server.HTTPServer(server_address, CodeHandler)
    httpd.handle_request()

    with open(REFRESH_FILE, 'w') as fp:
        fp.write(refresh_token)

    return access_token

if __name__ == "__main__":
    print(authenticate())
