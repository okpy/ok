
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

from flask import Blueprint, jsonify, request

import flask_restful as restful
from flask_restful import reqparse, fields, marshal_with

import datetime
import json

from flask_restful.representations.json import output_json

from functools import wraps

from flask.ext.login import current_user

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
    return json.loads(field)


@api.representation('application/json')
def envelope_api(data, code, headers=None):
    """ API response envelope (for metadata/pagination).
    Wraps JSON response in envelope to match v1 API output format.
    This is for successful requests only. Exceptions are handled elsewhere.

        data is the object returned by the API.
        code is the HTTP status code as an int
        message will always be sucess since the request did not fail.
    """
    data = {
        'data': data,
        'code': code,
        'message': 'success'
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
        kwargs['user'] = current_user
        return func(*args, **kwargs)
    return wrapper


def check_version(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        supplied = request.args.get('client_version', '')
        current_version, download_link = '2', ''  # TODO Actual Version Check
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


class Resource(restful.Resource):
    version = 'v3'
    method_decorators = [authenticate, check_version]
    # applies to all inherited resources

    def make_response(self, data, *args, **kwargs):
        data = {'data': data}
        return super().make_response(data, *args, **kwargs)

    def can(object, user, course, action):
        if user.is_admin:
            return True
        return False


class PublicResource(Resource):
    method_decorators = [check_version]


class v3Info(Resource):
    def get(self, user):
        return {
            'version': API_VERSION,
            'url': '/api/{}/'.format(API_VERSION),
            'documentation': 'http://github.com/Cal-CS-61A-Staff/ok/wiki'
        }

#  Fewer methods/APIs as V1 since the frontend will not use the API
#  TODO Permsisions for API actions


def make_backup(user, assignment, messages, submit, submitter):
    """
    Create backup with message objects.

    :param user: (object) caller
    :param assignment: (Assignment)
    :param messages: Data content of backup/submission
    :param submit: Whether this backup is a submission to be graded
    :param submitter: (object) caller or submitter
    :return: (Backup) backup
    """

    analytics = messages.get('analytics')

    if analytics:
        # message_date = analytics.get('time', None)
        client_time = datetime.datetime.now()
        # TODO client_time = parse_date(message_date)
    else:
        client_time = datetime.datetime.now()

    backup = models.Backup(client_time=client_time, submitter=user.id,
                           assignment=assignment.id, submit=submit)
    messages = [models.Message(kind=k, backup=backup,
                contents=m) for k, m in messages.iteritems()]
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


class BackupSchema(APISchema):

    get_fields = {
        'id': fields.Integer,
        'submitter': fields.Integer,
        'assignment': fields.Integer,
        'messages': fields.List(fields.Nested(MessageSchema.get_fields)),
        'client_time': fields.DateTime(dt_format='rfc822'),
        'created': fields.DateTime(dt_format='rfc822')
    }

    post_fields = {
        'id': fields.Integer,
        'url': fields.String,
        'message': fields.String,
    }

    def __init__(self):
        APISchema.__init__(self)
        self.parser.add_argument('assignment', type=str, required=True,
                                 help='Name of Assignment')
        self.parser.add_argument('messages', type=json_field, required=True,
                                 help='Backup Contents as JSON')

        # Optional - probably not needed now that there are two endpoints
        self.parser.add_argument('submit', type=bool,
                                 help='Flagged as a submission')
        self.parser.add_argument('submitter', help='Name of Assignment')

    def store_backup(self, user):
        args = self.parse_args()
        # TODO Assignment Memcache.
        assignment = models.Assignment.query.filter_by(
            name=args['assignment']).first()
        messages, submit, submitter = args['messages'], args['submit'], user
        backup = make_backup(user, assignment, messages, submit, submitter)
        return backup


class SubmissionSchema(BackupSchema):

    get_fields = {
        'id': fields.Integer,
        'assignment': fields.Integer,
        'submitter': fields.Integer,
        'backup': fields.Nested(BackupSchema.get_fields),
        'flagged': fields.Boolean,
        'revision': fields.Boolean,
        'created': fields.DateTime(dt_format='rfc822')
    }


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
        return {'id': backup.id,
                'message': "Backup Succesful",
                'url': 'tbd'}


class Submission(Resource):
    """ Submission resource.
        Authenticated. Permissions: >= Student/Staff
        Used by: Ok Client Submission.
    """
    model = models.Submission
    schema = SubmissionSchema()

    @marshal_with(schema.get_fields)
    def get(self, user, key=None):
        if key is None:
            restful.abort(405)
        submission = self.model.query.filter_by(id=key).first()
        # TODO CHECK .user obj
        if submission.user != user or not user.is_admin:
            restful.abort(403)
        return submission

    @marshal_with(schema.post_fields)
    def post(self, user, key=None):
        if key is not None:
            restful.abort(405)
        back = self.schema.store_backup(user)
        subm = models.Submission(backup=back.id, assignment=back.assignment,
                                 submitter=user.id)
        models.db.session.add(subm)
        models.db.session.commit()
        return {'id': subm.id,
                'message': "Submission Succesful",
                'url': 'tbd'}


class Score(Resource):
    """ Score creation resource.
        Authenticated. Permissions: >= Staff
        Used by: Autograder
    """
    model = models.Score

    def post(self, user):
        # TODO : Actual arg parse here (for autograder)
        score = models.Score(backup=1, score=1,
                             tag="test", grader=user.id)
        models.db.session.add(score)
        models.db.session.commit()

        return {'id': score.id, 'backup': 1}


class Enrollment(Resource):
    """ View what courses students are enrolled in.
        Authenticated. Permissions: >= User
        Used by: Ok Client Auth
    """
    model = models.Participant

    def get(self, email, user):
        course = request.args.get('course', '')  # TODO use reqparse
        if course:
            return {'created': str(datetime.datetime.now())}
        return {}

api.add_resource(v3Info, '/v3')

api.add_resource(Submission, '/v3/submission', '/v3/submission/<int:key>')
api.add_resource(Backup, '/v3/backup', '/v3/backup/<int:key>')
api.add_resource(Score, '/v3/score')
api.add_resource(Enrollment, '/v3/enrollment/<string:email>')
