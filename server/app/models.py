#pylint: disable=no-member

"""Data models."""

import datetime

from flask import Blueprint
from app import constants

MODEL_BLUEPRINT = Blueprint('models', __name__)

from app import app
from app.needs import Need
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
    def can(cls, user, need, obj=None):
        """
        Tells you if the |user| satisfies the given |need| for this object.
        """
        need.set_object(obj or cls)
        return cls._can(user, need, obj)

    @classmethod
    def _can(cls, user, need, obj=None):
        return False

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
    form = UserForm
    #TODO(martinis) figure out how to actually use this data
    courses = ndb.KeyProperty('Course', repeated=True)

    def __repr__(self):
        return '<User %r>' % self.email

    @property
    def is_admin(self):
        return self.role == constants.ADMIN_ROLE

    @property
    def is_staff(self):
        return self.role == constants.STAFF_ROLE

    @property
    def staffed_courses(self):
        return Course.query(Course.staff == self.key)

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        if 'email' not in values:
            raise ValueError("Need to specify an email")
        inst = cls(key=ndb.Key('User', values['email']))
        inst.populate(**values) #pylint: disable=star-args
        return inst

    @classmethod
    def get_or_insert(cls, email, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for users"
        kwargs['email'] = email
        return super(cls, User).get_or_insert(email, **kwargs)

    @classmethod
    def get_by_id(cls, id, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for users"
        return super(cls, User).get_by_id(id, **kwargs)

    @property
    def logged_in(self):
        return True

    @classmethod
    def _can(cls, user, need, obj=None):
        if not user.logged_in:
            return False
        
        if user.is_admin:
            return True
        action = need.action
        if action in ("get", "index"):
            if obj:
                if obj.key == user.key:
                    return True

            if user.is_staff:
                for course in user.staffed_courses:
                    if course.key in obj.courses:
                        return True
        return False

class AnonymousUser(User):
    @property
    def logged_in(self):
        return False

    def put(self, *args, **kwds):
        """
        Disable puts for Anonymous Users
        """
        pass

AnonymousUser = AnonymousUser()


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
    course = ndb.KeyProperty('Course')

    @classmethod
    def _can(cls, user, need, obj=None):
        action = need.action
        if action in ("get", "index"):
            return True
        elif action == "create":
            return user.is_admin
        return False


class Course(Base):
    """Courses have enrolled students and assignment lists with due dates."""
    institution = ndb.StringProperty() # E.g., 'UC Berkeley'
    name = ndb.StringProperty() # E.g., 'CS 61A'
    offering = ndb.StringProperty()  # E.g., 'Fall 2014'
    creator = ndb.StructuredProperty(User)
    staff = ndb.KeyProperty(User, repeated=True)

    @classmethod
    def _can(cls, user, need, obj=None):
        action = need.action
        if action == "get":
            return True
        elif action in ("create", "delete"):
            return user.is_admin
        elif action == "modify":
            if not obj:
                raise ValueError("Need instance for get action.")
            return user.key in obj.staff
        return False


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

    @classmethod
    def _can(cls, user, need, obj=None):
        action = need.action
        if action == "get":
            if not obj:
                raise ValueError("Need instance for get action.")
            if user.is_admin or obj.submitter == user.key:
                return True
            if user.is_staff:
                for course in user.staffed_courses:
                    if course.key in obj.submitter.get().courses:
                        return True
        return False

