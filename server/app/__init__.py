"""
Initialize Flask app.
"""

from flask import Flask

import os
from werkzeug.debug import DebuggedApplication

app = Flask('app') #pylint: disable=invalid-name

from app import constants
from app import models
from app import utils
from app import exceptions
from app import api
from app import auth
import app.analytics as analytics
from app.seed import seed, is_seeded

DEBUG = (os.environ['SERVER_SOFTWARE'].startswith('Dev')
         if 'SERVER_SOFTWARE' in os.environ
         else True)

TESTING = os.environ["FLASK_CONF"] == "TEST" if "FLASK_CONF" in os.environ else False
if DEBUG and not TESTING and not is_seeded():
    seed()

if DEBUG:
    app.config.from_object('app.settings.Debug')

    # Google app engine mini profiler
    # https://github.com/kamens/gae_mini_profiler
    app.wsgi_app = DebuggedApplication(app.wsgi_app, evalex=True)
else:
    app.config.from_object('app.settings.Production')

# Enable jinja2 loop controls extension
app.jinja_env.add_extension('jinja2.ext.loopcontrols')

# Pull in URL dispatch routes
import urls

# Import the authenticator. Central usage place.
import authenticator

# Set timezone
os.environ['TZ'] = constants.TIMEZONE
