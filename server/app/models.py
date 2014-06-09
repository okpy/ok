#pylint: disable=C0103
"""
Models
"""
from sqlalchemy.ext.declarative import declarative_base

from flask.ext.sqlalchemy import SQLAlchemy #pylint: disable=F0401,E0611
from flask import Blueprint
from app import constants

model_blueprint = Blueprint('models', __name__)

from app import app
from flask import json
from flask.json import JSONEncoder

db = SQLAlchemy(app)

class JSONEncoder(JSONEncoder):
    """
    Wrapper class to try calling an object's tojson() method. This allows
    us to JSONify objects coming from the ORM. Also handles dates and datetimes.
    """

    def default(self, obj):
        try:
            return obj.tojson()
        except AttributeError:
            return json.JSONEncoder.default(self, obj)

app.json_encoder = JSONEncoder

# Let's make this a class decorator
base = declarative_base()

class Base(object):
    """
    Add some default properties and methods to the SQLAlchemy declarative Base.
    """

    @property
    def columns(self):
        return [ c.name for c in self.__table__.columns ]

    @property
    def columnitems(self):
        return dict([ (c, getattr(self, c)) for c in self.columns ])

    def tojson(self):
        rval = self.columnitems
        return rval

class User(db.Model, Base): #pylint: disable=R0903
    """
    The User Model
    """
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    login = db.Column(db.String(30))
    role = db.Column(db.Integer, default=constants.STUDENT_ROLE)

    def __repr__(self):
        return '<User %r>' % self.email

class Assignment(db.Model, Base): #pylint: disable=R0903
    """
    The Assignment Model
    """
    id = db.Column(db.Integer, primary_key=True)
    submissions = db.relationship('Submission', backref="assignment")

    def __init__(self, *args, **kwds):
        db.Model.__init__(*args, **kwds)

class Submission(db.Model, Base): #pylint: disable=R0903
    """
    The Submission Model
    """
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))

    def __init__(self, *args, **kwds):
        db.Model.__init__(*args, **kwds)
