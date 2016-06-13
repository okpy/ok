import os

from markdown import markdown
from flask import Flask
from flask import Markup

from flask_rq import RQ
from flask_wtf.csrf import CsrfProtect

from webassets.loaders import PythonLoader as PythonAssetsLoader

from server import assets, converters, utils
from server.forms import CSRFForm
from server.models import db
from server.controllers.admin import admin
from server.controllers.api import endpoints as api
from server.controllers.auth import auth, login_manager
from server.controllers.student import student
from server.constants import API_PREFIX

from server.extensions import (
    cache,
    assets_env,
    debug_toolbar,
    csrf
)

def create_app(default_config_path=None):
    """Create and return a Flask application. Reads a config file path from the
    OK_SERVER_CONFIG environment variable. If it is not set, reads from
    default_config_path instead. This is so we can default to a development
    environment locally, but the app will fail in production if there is no
    config file rather than dangerously defaulting to a development environment.
    """

    app = Flask(__name__)

    config_path = os.getenv('OK_SERVER_CONFIG', default_config_path)
    if config_path is None:
        raise ValueError('No configuration file found'
            'Check that the OK_SERVER_CONFIG environment variable is set.')
    app.config.from_pyfile(config_path)

    # initialize redis task queues
    RQ(app)

    # initialize the cache
    cache.init_app(app)

    # Protect All Routes from csrf
    csrf.init_app(app)

    # initialize the debug tool bar
    debug_toolbar.init_app(app)

    # initialize SQLAlchemy
    db.init_app(app)

    login_manager.init_app(app)

    # Import and register the different asset bundles
    assets_env.init_app(app)
    assets_loader = PythonAssetsLoader(assets)
    for name, bundle in assets_loader.load_bundles().items():
        assets_env.register(name, bundle)

    # custom URL handling
    converters.init_app(app)

    # custom Jinja rendering
    app.jinja_env.globals.update({
        'utils': utils,
        'debug': app.debug,
        'CSRFForm': CSRFForm
    })

    app.jinja_env.filters.update({
        'markdown': lambda data: Markup(markdown(data))
    })

    # register our blueprints
    # OAuth should not need CSRF protection
    csrf.exempt(auth)
    app.register_blueprint(auth)

    app.register_blueprint(student)

    app.register_blueprint(admin, url_prefix='/admin')

    # API does not need CSRF protection
    csrf.exempt(api)
    app.register_blueprint(api, url_prefix=API_PREFIX)

    return app
