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

class JSONEncoder(old_json):
    """
    Wrapper class to try calling an object's to_dict() method. This allows
    us to JSONify objects coming from the ORM. Also handles dates & datetimes.
    """

    def default(self, obj): #pylint: disable=E0202
        if isinstance(obj, ndb.Key):
            got = obj.get()
            if not got:
                return None
            return got.to_json()
        elif isinstance(obj, datetime.datetime):
            obj = convert_timezone(obj)
            return str(obj)
        if isinstance(obj, ndb.Model):
            return obj.to_json()
        return super(JSONEncoder, self).default(obj)


app.json_encoder = JSONEncoder

def convert_timezone(utc_dt):
    delta = datetime.timedelta(hours = -7)
    return (datetime.datetime.combine(utc_dt.date(),utc_dt.time()) + delta)


class Base(ndb.Model):
    """Shared utilities."""

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        inst = cls()
        inst.populate(**values) #pylint: disable=star-args
        return inst

    def to_json(self, fields=None):
        """Converts this model to a json dictionary."""
        if not fields:
            fields = {}

        if fields:
            result = self.to_dict(include=fields.keys())
        else:
            result = self.to_dict()

        if self.key and (not fields or 'id' in fields):
            result['id'] = self.key.id()

        for key, value in result.items():
            if isinstance(value, ndb.Key):
                result[key] = value.get().to_json(fields.get(key))
            else:
                try:
                    new_value = app.json_encoder().default(value)
                    result[key] = new_value
                except TypeError:
                    pass
        return result

    @classmethod
    def can(cls, user, need, obj=None, query=None):
        """
        Tells you if the |user| satisfies the given |need| for this object.
        """
        need.set_object(obj or cls)
        return cls._can(user, need, obj, query)

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        return False


class User(Base):
    """Users."""
    email = ndb.StringProperty() # Must be associated with some OAuth login.
    login = ndb.StringProperty() # TODO(denero) Legacy of glookup system
    role = ndb.StringProperty(default=constants.STUDENT_ROLE)
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
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
        return super(User, cls).get_or_insert(email, **kwargs)

    @classmethod
    def get_by_id(cls, id, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for users"
        return super(User, cls).get_by_id(id, **kwargs)

    @property
    def logged_in(self):
        return True

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        if not user.logged_in:
            return False

        action = need.action
        if action == "get":
            if user.is_admin:
                return True
            if obj:
                if obj.key == user.key:
                    return True

            if user.is_staff:
                for course in user.staffed_courses:
                    if course.key in obj.courses:
                        return True
        elif action == "index":
            if user.is_admin:
                return query

            filters = []
            for course in user.courses:
                if user.key in course.staff:
                    filters.append(User.query().filter(
                        User.courses == course.key))

            filters.append(User.key == user.key)

            if len(filters) > 1:
                return query.filter(ndb.OR(*filters))
            else:
                return query.filter(filters[0])
        elif action in ("create", "put"):
            return user.is_admin
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

    @classmethod
    def get_or_insert(cls, *args, **kwds):
        return super(_AnonUserClass, cls).get_or_insert(*args, **kwds)

_AnonUserClass = AnonymousUser
_AnonUser = None

def AnonymousUser():
    global _AnonUser
    if not _AnonUser:
        _AnonUser = _AnonUserClass.get_or_insert("anon_user")
    return _AnonUser


class Assignment(Base):
    """
    The Assignment Model
    """
    name = ndb.StringProperty() # Must be unique to support submission.
    # TODO(denero) Validate uniqueness of name.
    points = ndb.FloatProperty()
    creator = ndb.KeyProperty(User)
    templates = ndb.JsonProperty()
    course = ndb.KeyProperty('Course')

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action
        if action == "get":
            return True
        elif action == "index":
            return query
        elif action in ("create", "put"):
            return user.is_admin
        return False


class Course(Base):
    """Courses have enrolled students and assignment lists with due dates."""
    institution = ndb.StringProperty() # E.g., 'UC Berkeley'
    name = ndb.StringProperty() # E.g., 'CS 61A'
    offering = ndb.StringProperty()  # E.g., 'Fall 2014'
    creator = ndb.KeyProperty(User)
    staff = ndb.KeyProperty(User, repeated=True)

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action
        if action == "get":
            return True
        elif action == "index":
            return query
        elif action in ("create", "delete", "put"):
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
    submitter = ndb.KeyProperty(User, required=True)
    assignment = ndb.KeyProperty(Assignment)
    messages = ndb.JsonProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
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
        if action in ("create", "put"):
            return user.logged_in

        if action == "index":
            if not user.logged_in:
                return False

            if not query:
                raise ValueError(
                        "Need query instance for Submission index action")

            if user.is_admin:
                return query

            courses = user.courses
            filters = []
            for course in courses:
                if user.key in course.staff:
                    assignments = Assignment.query().filter(
                        Assignment.course == course.key)
                    filters.append(Submission.assignment.IN(
                        assignments.get()))

            filters.append(Submission.submitter == user.key)

            if len(filters) > 1:
                return query.filter(ndb.OR(*filters))
            else:
                return query.filter(filters[0])
        return False


class SubmissionDiff(Base):
    submission = ndb.KeyProperty(Submission)
    diff = ndb.JsonProperty()


class Version(Base):
    """A version of client-side resources. Used for auto-updating."""
    name = ndb.StringProperty()
    versions = ndb.StringProperty(repeated=True)
    current_version = ndb.StringProperty()
    base_url = ndb.StringProperty()

    def to_json(self, fields=None):
        json = super(Version, self).to_json(fields)
        if self.current_version:
            json['current_download_link'] = '/'.join((
                self.base_url, self.current_version, self.name))

        return json

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action

        if action == "delete":
            return False
        if action == "index":
            return query
        return user.is_admin

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        if 'name' not in values:
            raise ValueError("Need to specify a name")
        inst = cls(key=ndb.Key('Version', values['name']))
        inst.populate(**values) #pylint: disable=star-args
        return inst

    @classmethod
    def get_or_insert(cls, key, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for versions"
        kwargs['name'] = key
        return super(cls, Version).get_or_insert(key, **kwargs)

    @classmethod
    def get_by_id(cls, key, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for versions"
        return super(cls, Version).get_by_id(key, **kwargs)
