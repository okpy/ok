import os

from markdown import markdown
from flask import Flask, render_template, g, request
from flask import Markup
from flask_rq import RQ
from flask_wtf.csrf import CsrfProtect
from webassets.loaders import PythonLoader as PythonAssetsLoader
from werkzeug.contrib.fixers import ProxyFix

from server import assets, converters, utils
from server.forms import CSRFForm
from server.models import db
from server.controllers.about import about
from server.controllers.admin import admin
from server.controllers.api import endpoints as api_endpoints
from server.controllers.api import api  # Flask Restful API
from server.controllers.auth import auth, login_manager
from server.controllers.oauth import oauth
from server.controllers.student import student
from server.constants import API_PREFIX

from server.extensions import (
    assets_env,
    cache,
    csrf,
    debug_toolbar,
    oauth_provider,
    sentry
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

    # Senty Error Reporting & Other Prod Changes
    sentry_dsn = os.getenv('SENTRY_DSN')
    if not app.debug:
        app.wsgi_app = ProxyFix(app.wsgi_app)
        if sentry_dsn:
            sentry.init_app(app, dsn=sentry_dsn)

            @app.errorhandler(500)
            def internal_server_error(error):
                return render_template('errors/500.html',
                    event_id=g.sentry_event_id,
                    public_dsn=sentry.client.get_public_dsn('https')
                ), 500

    @app.errorhandler(404)
    def not_found_error(error):
        if request.path.startswith("/api"):
            return api.handle_error(error)
        return render_template('errors/404.html'), 404

    # initialize the cache
    cache.init_app(app)

    # initialize redis task queues
    RQ(app)

    # Protect All Routes from csrf
    csrf.init_app(app)

    # initialize the debug tool bar
    debug_toolbar.init_app(app)

    # initialize SQLAlchemy
    db.init_app(app)

    # Flask-Login manager
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
        'instantclick': app.config.get('INSTANTCLICK', True),
        'CSRFForm': CSRFForm
    })

    app.jinja_env.filters.update({
        'markdown': lambda data: Markup(markdown(data)),
        'pluralize': utils.pluralize
    })

    # register our blueprints
    # OAuth should not need CSRF protection
    csrf.exempt(auth)
    app.register_blueprint(auth)

    csrf.exempt(oauth)
    app.register_blueprint(oauth)

    app.register_blueprint(student)

    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(about, url_prefix='/about')

    # API does not need CSRF protection
    csrf.exempt(api_endpoints)
    app.register_blueprint(api_endpoints, url_prefix=API_PREFIX)

    return app
