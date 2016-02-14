"""
API.py - /api/{version}/endpoints

    The API provides an interface for external clients to interface with
    the server.

    Primary Clients: OK client, Server-side Autograder
    Other Clients: Some front-end features. Research Code

    Example of defining a new API:

    class UserAPI(Resource):
        def get(self, user):
            return {'id': user.id}

    api.add_resource(UserAPI, '/v3/user')
"""

import datetime
import json
from functools import wraps

from flask import Blueprint, jsonify, request
from flask.ext.login import current_user
import flask_restful as restful
from flask_restful import reqparse, fields, marshal_with
from flask_restful.representations.json import output_json

from server.extensions import cache
from server.utils import encode_id
import server.models as models



endpoints = Blueprint('api', __name__)
endpoints.config = {}

@endpoints.record
def record_params(setup_state):
    """ Load used app configs into local config on registration from
    server/__init__.py """
    app = setup_state.app
    endpoints.config['tz'] = app.config.get('TIMEZONE', 'utc')  # sample config


api = restful.Api(endpoints, catch_all_404s=True)

API_VERSION = 'v3'


def json_field(field):
    """
    Parses field or list, or returns appropriate boolean value.

    :param field: (string)
    :return: (string) parsed JSON
    """
    if not field[0] in ['{', '[']:
        if field == 'false':
            return False
        elif field == 'true':
            return True
        return field
    return json.dumps(field)


@api.representation('application/json')
def envelope_api(data, code, headers=None):
    """ API response envelope (for metadata/pagination).
    Wraps JSON response in envelope to match v1 API output format.
    This is for successful requests only. Exceptions are handled elsewhere.

        data is the object returned by the API.
        code is the HTTP status code as an int
        message will always be sucess since the request did not fail.
    """
    message = 'success'
    if 'message' in data:
        message = data['message']
        del data['message']
    data = {
        'data': data,
        'code': code,
        'message': message
    }
    return output_json(data, code, headers)


def authenticate(func):
    """ Provide user object to API methods. Passes USER as a keyword argument
        to all protected API Methods.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Public methods do not need authentication
        if not getattr(func, 'public', False) and not current_user.is_authenticated:
            restful.abort(401)
        # The login manager takes care of converting a token to a user.
        kwargs['user'] = current_user
        return func(*args, **kwargs)
    return wrapper


def check_version(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        supplied = request.args.get('client_version')
        client = request.args.get('client_name', 'ok') # ok-client doesn't send this right now
        current_version, download_link = get_current_version(client)
        if not supplied or supplied == current_version:
            return func(*args, **kwargs)

        message = ("Incorrect client version. Supplied version was {}. " +
                   "Correct version is {}.").format(supplied, current_version)
        data = {
            'supplied': supplied,
            'correct': current_version,
            'download_link': download_link
        }

        response = jsonify(**{
            'status': 403,
            'message': message,
            'data': data
        })
        response.status_code = 403
        return response
    return wrapper

@cache.memoize(1000)
def name_to_assign_id(name):
    assgn = models.Assignment.query.filter_by(name=name).one_or_none()
    if assgn:
        return assgn.id

@cache.memoize(1000)
def get_current_version(name):
    version = models.Version.query.filter_by(name=name).one_or_none()
    if version:
        return version.current_version, version.download_link
    return None, None

class Resource(restful.Resource):
    version = 'v3'
    method_decorators = [authenticate, check_version]
    # applies to all inherited resources

    def __repr__(self):
        return "<Resource {}>".format(self.__class__.__name__)

    def make_response(self, data, *args, **kwargs):
        return super().make_response(data, *args, **kwargs)

    def can(object, user, course, action):
        if user.is_admin:
            return True
        return False


class PublicResource(Resource):
    method_decorators = []

class v3Info(PublicResource):
    def get(self):
        return {
            'version': API_VERSION,
            'url': '/api/{}/'.format(API_VERSION),
            'documentation': 'http://github.com/Cal-CS-61A-Staff/ok/wiki'
        }

#  Fewer methods/APIs as V1 since the frontend will not use the API
#  TODO Permsisions for API actions

def make_backup(user, assignment_id, messages, submit):
    """
    Create backup with message objects.

    :param user: (object) caller
    :param assignment_id: (int) Assignment ID
    :param messages: Data content of backup/submission
    :param submit: Whether this backup is a submission to be graded
    :return: (Backup) backup
    """

    analytics = messages.get('analytics')

    if analytics:
        # message_date = analytics.get('time', None)
        client_time = datetime.datetime.now()
        # TODO client_time = parse_date(message_date)
    else:
        client_time = datetime.datetime.now()

    backup = models.Backup(client_time=client_time, submitter=user,
                           assignment_id=assignment_id, submit=submit)
    messages = [models.Message(kind=k, backup=backup,
                contents=m) for k, m in messages.items()]
    backup.messages = messages
    models.db.session.add_all(messages)
    models.db.session.add(backup)
    models.db.session.commit()
    return backup


class APISchema():
    """ APISchema describes the input and output formats for
    resources. The parser deals with arguments to the API.
    The API responses are marshalled to json through get_fields
    """
    get_fields = {
        'id': fields.Integer,
        'created': fields.DateTime(dt_format='rfc822')
    }

    def __init__(self):
        self.parser = reqparse.RequestParser()

    def parse_args(self):
        return self.parser.parse_args()


class MessageSchema(APISchema):
    """ Messages do not have their own API (currently).
    They are displayed through the backup/submission APIs.
    """
    get_fields = {
        'kind': fields.String,
        'contents': fields.String,
        'created': fields.DateTime(dt_format='rfc822')
    }

class CourseSchema(APISchema):
    get_fields = {
        'id': fields.Integer,
        'offering': fields.String,
        'display_name': fields.String,
        'active': fields.Boolean,
    }


class BackupSchema(APISchema):

    get_fields = {
        'id': fields.Integer,
        'submitter': fields.String,
        'assignment': fields.String,
        'messages': fields.List(fields.Nested(MessageSchema.get_fields)),
        'client_time': fields.DateTime(dt_format='rfc822'),
        'created': fields.DateTime(dt_format='rfc822')
    }

    post_fields = {
        'email': fields.String,
        'key': fields.String,
        'course': fields.Nested(CourseSchema.get_fields),
        'assignment': fields.String,
    }

    def __init__(self):
        APISchema.__init__(self)
        self.parser.add_argument('assignment', type=str, required=True,
                                 help='Name of Assignment')
        self.parser.add_argument('messages', type=dict, required=True,
                                 help='Backup Contents as JSON')
        self.parser.add_argument('submit', type=bool, default=False,
                                 help='Flagged as a submission')

    def store_backup(self, user):
        args = self.parse_args()
        # TODO Assignment Memcache.
        assignment_id = name_to_assign_id(args['assignment'])
        messages, submit = args['messages'], args['submit']
        backup = make_backup(user, assignment_id, messages, submit)
        return backup



class ParticipationSchema(APISchema):
    get_fields = {
        'course_id': fields.Integer,
        'role': fields.String,
        'course': fields.Nested(CourseSchema.get_fields),
    }

class EnrollmentSchema(APISchema):

    get_fields = {
        'courses': fields.List(fields.Nested(ParticipationSchema.get_fields))
    }

class VersionSchema(APISchema):

    version_fields = {
        'name': fields.String(),
        'current_version': fields.String(),
        'download_link': fields.String(),
    }

    get_fields = {
        'results': fields.List(fields.Nested(version_fields))
    }


# TODO: should be two classes, one for /backups/ and one for /backups/<int:key>/
class Backup(Resource):
    """ Submission retreival resource.
        Authenticated. Permissions: >= User/Staff
        Used by: Ok Client Submission/Exports.
    """
    schema = BackupSchema()
    model = models.Backup

    @marshal_with(schema.get_fields)
    def get(self, user, key=None):
        if key is None:
            restful.abort(405)
        backup = self.model.query.filter_by(id=key).first()
        # TODO CHECK
        if backup.user != user or not user.is_admin:
            restful.abort(403)
        return backup

    @marshal_with(schema.post_fields)
    def post(self, user, key=None):
        if key is not None:
            restful.abort(405)
        backup = self.schema.store_backup(user)
        return {
            'email': current_user.email,
            'key': encode_id(backup.id),
            'course': backup.assignment.course,
            'assignment': backup.assignment.name
        }


class Enrollment(Resource):
    """ View what courses an email is enrolled in.
        Authenticated. Permissions: >= User or admins.
        Used by: Ok Client Auth
    """
    model = models.Enrollment
    schema = EnrollmentSchema()

    @marshal_with(schema.get_fields)
    def get(self, user, email):
        target = models.User.lookup(email)
        if not self.can('view', target, user):
            restful.abort(403)
        if target:
            return {'courses': user.participations}
        return {'courses': []}

    @staticmethod
    def can(action, resource, requester):
        if requester.is_admin:
            return True
        return resource == requester

class Version(PublicResource):
    """ Current version of a client
    Permissions: World Readable
    Used by: Ok Client Auth
    """
    model = models.Version
    schema = VersionSchema()

    @marshal_with(schema.get_fields)
    @cache.memoize(600)
    def get(self, name=None):
        if name:
            versions = self.model.query.filter_by(name=name).all()
        else:
            versions = self.model.query.all()
        return {'results': versions}


api.add_resource(v3Info, '/v3/')

api.add_resource(Backup, '/v3/backups/', '/v3/backups/<int:key>/')
api.add_resource(Enrollment, '/v3/enrollment/<string:email>/')
api.add_resource(Version, '/v3/version/', '/v3/version/<string:name>')
