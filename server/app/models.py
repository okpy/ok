#pylint: disable=C0103,no-member
"""
Models
"""
from flask import Blueprint
from app import constants

model_blueprint = Blueprint('models', __name__)

from app import app
from flask import json
from flask.json import JSONEncoder as old_json

from google.appengine.ext import ndb

class JSONEncoder(old_json):
    """
    Wrapper class to try calling an object's to_dict() method. This allows
    us to JSONify objects coming from the ORM. Also handles dates & datetimes.
    """

    def default(self, obj): #pylint: disable=E0202
        if isinstance(obj, ndb.Key):
            return obj.id()
        try:
            return obj.to_dict()
        except AttributeError:
            return json.JSONEncoder.default(self, obj)

app.json_encoder = JSONEncoder

class Base(ndb.Model):
    """
    Add some default properties and methods to the SQLAlchemy declarative Base.
    """
    @classmethod
    def from_dict(cls, values):
        """
        Creates an instance from the given values
        """
        inst = cls()
        inst.populate(**values)
        return inst

class Submission(Base): #pylint: disable=R0903
    """
    The Submission Model
    """
    location = ndb.StringProperty()

class User(Base): #pylint: disable=R0903
    """
    The User Model
    """
    email = ndb.StringProperty()
    login = ndb.StringProperty()
    role = ndb.IntegerProperty(default=constants.STUDENT_ROLE)
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    submissions = ndb.StructuredProperty(Submission, repeated=True)

    def __repr__(self):
        return '<User %r>' % self.email

class Assignment(Base): #pylint: disable=R0903
    """
    The Assignment Model
    """
    name = ndb.StringProperty()
    points = ndb.IntegerProperty()
    submissions = ndb.StructuredProperty(Submission, repeated=True)

