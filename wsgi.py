#!/usr/bin/env python3
# To run:
# gunicorn -b 0.0.0.0:5000 wsgi:app
import os

from werkzeug.contrib.fixers import ProxyFix

from server import create_app

env = os.environ.get('OK_ENV', 'dev')
app = create_app('settings/{0!s}.py'.format(env))

app.wsgi_app = ProxyFix(app.wsgi_app)
