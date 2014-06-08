import flask.ext.restless

from app import app, models
from app.models import db

# Create the Flask-Restless API manager.
manager = flask.ext.restless.APIManager(app, flask_sqlalchemy_db=db)

# Create API endpoints, which will be available at /api/<tablename> by
# default. Allowed HTTP methods can be specified as well.
manager.create_api(models.User, methods=['GET', 'POST', 'DELETE'], url_prefix='/api/v1')
manager.create_api(models.Assignment, methods=['GET'], url_prefix='/api/v1')
manager.create_api(models.Submission, methods=['GET'], url_prefix='/api/v1')
