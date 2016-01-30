#! ../env/bin/python

from flask import Flask
from flask.ext.rq import RQ
from hashids import Hashids
from webassets.loaders import PythonLoader as PythonAssetsLoader
from werkzeug.routing import BaseConverter

from server import assets
from server.models import db
from server.controllers.admin import admin
from server.controllers.api import endpoints as api
from server.controllers.auth import auth, login_manager
from server.controllers.main import main
from server.controllers.student import student

from server.constants import API_PREFIX

from server.extensions import (
    cache,
    assets_env,
    debug_toolbar
)

class HashidConverter(BaseConverter):
    # ID hashing configuration.
    # DO NOT CHANGE ONCE THE APP IS PUBLICLY AVAILABLE. You will break every
    # link with an ID in it.
    hashids = Hashids(min_length=6)

    def to_python(self, value):
        return self.hashids.decode(value)

    def to_url(self, value):
        return self.hashids.encode(value)

def create_app(object_name):
    """
    An flask application factory, as explained here:
    http://flask.pocoo.org/docs/patterns/appfactories/

    Arguments:
        object_name: the python path of the config object,
                     e.g. appname.settings.ProdConfig
    """

    app = Flask(__name__)

    app.config.from_object(object_name)

    # initialize redis task queues
    RQ(app)

    # initialize the cache
    cache.init_app(app)

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
    app.url_map.converters['hashid'] = HashidConverter

    # register our blueprints
    app.register_blueprint(main)

    app.register_blueprint(auth)

    app.register_blueprint(admin, url_prefix='/admin')

    app.register_blueprint(student, url_prefix='/student')

    app.register_blueprint(api, url_prefix=API_PREFIX)

    return app
