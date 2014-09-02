"""
Initialize Flask app.
"""

from flask import Flask

import os
from werkzeug.debug import DebuggedApplication

app = Flask('app') #pylint: disable=invalid-name

from app.models import MODEL_BLUEPRINT
from app import constants
from app import utils
from app import api
from app import auth


app.register_blueprint(MODEL_BLUEPRINT)
DEBUG = (os.environ['SERVER_SOFTWARE'].startswith('Dev')
            if 'SERVER_SOFTWARE' in os.environ
            else True)

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
