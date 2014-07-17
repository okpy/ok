"""Public client API for submission."""

from flask.views import MethodView
from flask.app import request
from flask import json

from app import app
from app import models
from app.decorators import admin_required

# TODO
