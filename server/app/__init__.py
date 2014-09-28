"""
Initialize Flask app.
"""

from flask import Flask

import os
from werkzeug.debug import DebuggedApplication

app = Flask('app') #pylint: disable=invalid-name

from app.models import MODEL_BLUEPRINT
from app import constants
from app import exceptions
from app import utils
from app import api
from app import auth

def seed():
    import datetime
    from google.appengine.ext import ndb

    def make_fake_course(creator):
        return models.Course(
            name="cs61a",
            institution="UC Soumya",
            term="Fall",
            year="2014",
            creator=creator.key,
            staff=[])

    def make_fake_assignment(course, creator):
        return models.Assignment(
            name='hw1',
            points=3,
            display_name="Hog",
            templates={},
            course=course.key,
            creator=creator.key,
            max_group_size=4,
            due_date=datetime.datetime.now())

    c = models.User(
                    key=ndb.Key("User", "dummy@admin.com"),
                    email="dummy@admin.com",
                    first_name="Admin",
                    last_name="Jones",
                    login="albert",
                    role="admin"
                )
    course = make_fake_course(c)
    course.put()
    assign = make_fake_assignment(course, c)
    assign.put()

app.register_blueprint(MODEL_BLUEPRINT)
DEBUG = (os.environ['SERVER_SOFTWARE'].startswith('Dev')
         if 'SERVER_SOFTWARE' in os.environ
         else True)
if len(list(models.Course.query().filter(models.Course.name == 'cs61a'))) == 0:
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
