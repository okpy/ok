#pylint: disable=no-member

"""Data models."""

import datetime

from flask import Blueprint
from app import constants

MODEL_BLUEPRINT = Blueprint('models', __name__)

from app import app
from app.permissions import Permission
from flask import json
from flask.json import JSONEncoder as old_json

from google.appengine.ext import db, ndb

BadValueError = db.BadValueError


class JSONEncoder(old_json):
    """
    Wrapper class to try calling an object's to_dict() method. This allows
    us to JSONify objects coming from the ORM. Also handles dates & datetimes.
    """

    def default(self, obj): #pylint: disable=E0202
        if isinstance(obj, ndb.Key):
            return obj.id()
        elif isinstance(obj, datetime.datetime):
            return str(obj)
        if isinstance(obj, ndb.Model):
            return obj.to_json()
        return super(JSONEncoder, self).default(obj)


app.json_encoder = JSONEncoder


class Base(ndb.Model):
    """Shared utilities."""

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        inst = cls()
        inst.populate(**values) #pylint: disable=star-args
        return inst

    def to_json(self):
        """Converts this model to a json dictionary."""
        result = self.to_dict()
        for key, value in result.items():
            try:
                new_value = app.json_encoder().default(value)
                result[key] = new_value
            except TypeError:
                pass
        return result

class UserPermission(Permission):
    name = "user"

    def satisfies(self, user):
        return user.key == self._obj.key

class User(Base):
    """Users."""
    email = ndb.StringProperty() # Must be associated with some OAuth login.
    login = ndb.StringProperty() # TODO(denero) Legacy of glookup system
    role = ndb.StringProperty(default=constants.STUDENT_ROLE)
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()

    def __repr__(self):
        return '<User %r>' % self.email

    @classmethod
    def get_or_insert(cls, email, **kwargs):
        kwargs['email'] = email
        return super(cls, User).get_or_insert('<%s>' % email, **kwargs)

    def attempt_access(self, resource):
        for permission in resource.permissions:
            if not permission.satisfies(self):
                return permission

    @property
    def permissions(self):
        return [UserPermission(self)]

class AssignmentPermission(Permission):
    name = "assignment"

    def satisfies(self, user):
        return True

class Assignment(Base):
    """
    The Assignment Model
    """
    name = ndb.StringProperty() # Must be unique to support submission.
    # TODO(denero) Validate uniqueness of name.
    points = ndb.FloatProperty()
    creator = ndb.KeyProperty(User)

    @property
    def permissions(self):
        return [AssignmentPermission(self)]


class Course(Base):
    """Courses have enrolled students and assignment lists with due dates."""
    institution = ndb.StringProperty() # E.g., 'UC Berkeley'
    name = ndb.StringProperty() # E.g., 'CS 61A'
    offering = ndb.StringProperty()  # E.g., 'Fall 2014'
    assignments = ndb.KeyProperty(Assignment, repeated=True)
    due_dates = ndb.DateTimeProperty(repeated=True)
    creator = ndb.StructuredProperty(User)


def validate_messages(_, messages):
    """Messages is a JSON string encoding a map from protocols to data."""
    if not messages:
        raise BadValueError('Empty messages')
    try:
        files = json.loads(messages)
        if not isinstance(files, dict):
            raise BadValueError('messages is not a JSON map')
        for k in files:
            if not isinstance(k, (str, unicode)):
                raise BadValueError('key %r is not a string' % k)
        # TODO(denero) Check that each key corresponds to a known protocol,
        #              and call protocol-specific validators on each value.
    except Exception as exc:
        raise BadValueError(exc)

class SubmissionPermission(Permission):
    name = "submission"

    def satisfies(self, user):
        return self._obj.submitter == user.key # or user.is_admin

class Submission(Base):
    """A submission is generated each time a student runs the client."""
    submitter = ndb.KeyProperty(User)
    assignment = ndb.KeyProperty(Assignment)
    messages = ndb.StringProperty(validator=validate_messages)
    created = ndb.DateTimeProperty(auto_now_add=True)

    @property
    def permissions(self):
        return [SubmissionPermission(self)]

