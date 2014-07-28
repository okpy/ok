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

from google.appengine.ext import db, ndb

# Exception class for validation errors (exported to the rest of the app).
BadValueError = db.BadValueError


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

    def to_dict(self):
        result = super(Base, self).to_dict()
        result['key'] = self.key.id() #get the key as a string
        return result

class Submission(Base): #pylint: disable=R0903
    """
    The Submission Model
    """

    @staticmethod
    def validate_contents(contents):
        """Contents encodes a JSON map from file paths to file contents."""
        if not contents:
            raise BadValueError('Empty contents')
        try:
            files = json.loads(contents)
            if not isinstance(files, dict):
                raise BadValueError('Contents is not a JSON map')
            for k, v in files.items():
                if not isinstance(k, (str, unicode)):
                    raise BadValueError('key %r is not a string' % k)
                if not isinstance(v, (str, unicode)):
                    raise BadValueError('key %r is not a string' % v)
                # TODO(denero) Validate that .py files have expected contents.
        except Exception as e:
            raise BadValueError(e)

    submitter = ndb.UserProperty()
    assignment = ndb.StructuredProperty(Assignment)
    contents = ndb.StringProperty(validator=validate_contents)
    date = ndb.DateTimeProperty(auto_now_add=True)
    location = ndb.StringProperty() # TODO(denero) What's this? Document or delete.


class User(Base): #pylint: disable=R0903
    """
    The User Model
    """
    email = ndb.StringProperty()
    login = ndb.StringProperty()
    role = ndb.StringProperty(default=constants.STUDENT_ROLE)
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

    def __repr__(self):
        return '<Assignment %r>' % self.name

