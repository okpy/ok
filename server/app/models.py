#pylint: disable=no-member
"""Models."""
from flask import Blueprint
from app import constants

model_blueprint = Blueprint('models', __name__)

from app import app
from flask import json
from flask.json import JSONEncoder as old_json

from google.appengine.ext import db,ndb

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
    """Shared utilities."""

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        inst = cls()
        inst.populate(**values)
        return inst

    def to_dict(self):
        result = super(Base, self).to_dict()
        if self.key:
            result['key'] = self.key.id() # Add the key as a string
        return result


class User(Base):
    """Users."""
    email = ndb.StringProperty() # Must be associated with some OAuth login.
    login = ndb.StringProperty() # TODO(denero) Legacy of glookup system
    role = ndb.StringProperty(default=constants.STUDENT_ROLE)
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()

    def __repr__(self):
        return '<User %r>' % self.email


class Assignment(Base):
    """
    The Assignment Model
    """
    name = ndb.StringProperty() # Must be unique to support submission.
    # TODO(denero) Validate uniqueness of name.
    points = ndb.FloatProperty()
    creator = ndb.StructuredProperty(User)


def validate_contents(contents):
    """Contents is a JSON string encoding a map from protocols to data."""
    if not contents:
        raise BadValueError('Empty contents')
    try:
        files = json.loads(contents)
        if not isinstance(files, dict):
            raise BadValueError('Contents is not a JSON map')
        for k in files:
            if not isinstance(k, (str, unicode)):
                raise BadValueError('key %r is not a string' % k)
        # TODO(denero) Check that each key corresponds to a known protocol,
        #              and call protocol-specific validators on each value.
    except Exception as e:
        raise BadValueError(e)


class Submission(Base):
    """A submission is generated each time a student runs the client."""
    submitter = ndb.UserProperty()
    assignment = ndb.StructuredProperty(Assignment)
    contents = ndb.StringProperty(validator=validate_contents)
    date = ndb.DateTimeProperty(auto_now_add=True)
