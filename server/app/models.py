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

from flask_wtf import Form
from wtforms import Field
from wtforms import TextField, IntegerField
from wtforms import validators
from wtforms.validators import ValidationError
from wtforms import widgets

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
        inst.populate(**values) #pylint: disable=star-args
        return inst

    def to_dict(self):
        result = super(Base, self).to_dict()
        if self.key:
            result['key'] = self.key.id() # Add the key as a string
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
        print field.data


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
    name = ndb.StringProperty()
    points = ndb.IntegerProperty()
    submissions = ndb.StructuredProperty(Submission, repeated=True)

    form = AssignmentForm

