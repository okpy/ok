#pylint: disable=no-member

"""Data models."""

import datetime

from flask import Blueprint
from app import constants

MODEL_BLUEPRINT = Blueprint('models', __name__)

from app import app
from flask import json
from flask.json import JSONEncoder as old_json

from google.appengine.ext import db, ndb

BadValueError = db.BadValueError

from flask_wtf import Form
from wtforms import Field
from wtforms import TextField, IntegerField
from wtforms import validators
from wtforms.validators import ValidationError
from wtforms import widgets

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

    @classmethod
    def new_form(cls):
        return cls.form(csrf_enabled=app.config['CSRF_ENABLED'])

def invalid_project_name(name):
    gotten = Assignment.query(Assignment.name == name).count()
    return not gotten == 1


class SubmissionField(Field):
    # Internal data is stored as actual Assignment object
    widget = widgets.TextInput

    def _value(self):
        return self.data

    def process_formdata(self, valuelist):
        name = valuelist[0]
        gotten = Assignment.query(Assignment.name == name).fetch(2)
        if not gotten or len(gotten) > 1:
            self.data = None
            return

        self.data = gotten[0]


class SubmissionForm(Form):
    project_name = SubmissionField('project_name', validators=[validators.DataRequired()])
    location = TextField()

    def validate_project_name(self, field): #pylint: disable=no-self-use
        if not field.data:
            raise ValidationError('Invalid project name')


class Submission(Base): #pylint: disable=R0903
    """
    The Submission Model
    """
    location = ndb.StringProperty()
    form = SubmissionForm


class UserForm(Form):
    email = TextField(validators=[validators.Email()])
    role = IntegerField()
    first_name = TextField()
    last_name = TextField()
    login = TextField()

class User(Base):
    """Users."""
    email = ndb.StringProperty() # Must be associated with some OAuth login.
    login = ndb.StringProperty() # TODO(denero) Legacy of glookup system
    role = ndb.IntegerProperty(default=constants.STUDENT_ROLE)
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    submissions = ndb.StructuredProperty(Submission, repeated=True)
    form = UserForm

    def __repr__(self):
        return '<User %r>' % self.email


class AssignmentForm(Form):
    name = TextField()
    points = TextField()


class Assignment(Base): #pylint: disable=R0903
    """
    The Assignment Model
    """
    name = ndb.StringProperty() # Must be unique to support submission.
    # TODO(denero) Validate uniqueness of name.
    points = ndb.FloatProperty()
    creator = ndb.KeyProperty(User)
    form = AssignmentForm


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


class Submission(Base):
    """A submission is generated each time a student runs the client."""
    submitter = ndb.KeyProperty(User)
    assignment = ndb.KeyProperty(Assignment)
    messages = ndb.StringProperty(validator=validate_messages)
    created = ndb.DateTimeProperty(auto_now_add=True)

    form = AssignmentForm

