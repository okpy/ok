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

import json
from functools import wraps

from flask import Blueprint, jsonify, request, url_for
from flask_login import current_user
import flask_restful as restful
from flask_restful import reqparse, fields, marshal_with
from flask_restful.representations.json import output_json

from server.extensions import cache
from server.utils import encode_id, decode_id
import server.models as models
from server.autograder import submit_continous

endpoints = Blueprint('api', __name__)
endpoints.config = {}


@endpoints.record
def record_params(setup_state):
    """ Load used app configs into local config on registration from
    server/__init__.py """
    app = setup_state.app
    endpoints.config['tz'] = app.config.get('TIMEZONE', 'utc')  # sample config
    endpoints.config['debug'] = app.debug


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


class HashIDField(fields.Raw):
    def format(self, value):
        if type(value) == int:
            return encode_id(value)
        else:
            return decode_id(value)

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
    # TODO: Require API token for all requests to API.
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
        # ok-client doesn't send client_name right now
        client = request.args.get('client_name', 'ok-client')
        current_version, download_link = models.Version.get_current_version(
            client)
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


def make_backup(user, assignment_id, messages, submit):
    """
    Create backup with message objects.

    :param user: (object) caller
    :param assignment: (int) Assignment ID
    :param messages: Data content of backup/submission
    :param submit: Whether this backup is a submission to be graded
    :return: (Backup) backup
    """
    backup = models.Backup(submitter=user, assignment_id=assignment_id,
                           submit=submit)
    backup.messages = [models.Message(kind=k, contents=m)
                       for k, m in messages.items()]
    models.db.session.add(backup)
    models.db.session.commit()
    return backup


def make_score(user, backup, score, message, kind):
    if not models.Backup.can(backup, user, 'grade'):
        return
    existing = models.Score.query.filter_by(backup=backup, kind=kind).first()
    if existing:
        existing.public = False
        existing.archived = True

    score = models.Score(grader_id=user.id, assignment=backup.assignment,
                         backup=backup, score=score, message=message,
                         kind=kind)
    models.db.session.add(score)
    models.db.session.commit()
    return score

class APISchema():
    """ APISchema describes the input and output formats for
    resources. The parser deals with arguments to the API.
    The API responses are marshalled to json through get_fields
    """
    get_fields = {
        'id': fields.Integer,
        'created': fields.DateTime(dt_format='iso8601')
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
        'contents': fields.Raw,
        'created': fields.DateTime(dt_format='iso8601')
    }


class CourseSchema(APISchema):
    get_fields = {
        'id': fields.Integer,
        'offering': fields.String,
        'display_name': fields.String,
        'active': fields.Boolean,
    }


class UserSchema(APISchema):
    get_fields = {
        'id': HashIDField,
        'email': fields.String,
    }


class AssignmentSchema(APISchema):
    get_fields = {
        'course': fields.Nested(CourseSchema.get_fields),
        'name': fields.String,
    }


class BackupSchema(APISchema):
    get_fields = {
        'id': HashIDField,  # Use Hash ID
        'submitter': fields.Nested(UserSchema.get_fields),
        'assignment': fields.Nested(AssignmentSchema.get_fields),
        'messages': fields.List(fields.Nested(MessageSchema.get_fields)),
        'created': fields.DateTime(dt_format='iso8601'),
        'is_late': fields.Boolean,
        'submit': fields.Boolean,
        'group': fields.List(fields.Nested(UserSchema.get_fields)),
    }

    export_fields = {
        'messages': fields.List(fields.Nested(MessageSchema.get_fields)),
        'created': fields.DateTime(dt_format='iso8601'),
        'is_late': fields.Boolean,
        'submit': fields.Boolean,
    }

    export_list = {
        'backups': fields.List(fields.Nested(export_fields)),
        'count': fields.Integer,
        'limit': fields.Integer,
        'offset': fields.Integer,
        'has_more': fields.Boolean
    }

    full_export_list = {
        'backups': fields.List(fields.Nested(get_fields)),
        'count': fields.Integer,
        'limit': fields.Integer,
        'offset': fields.Integer,
        'has_more': fields.Boolean
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
        assignment = models.Assignment.name_to_assign_info(args['assignment'])

        if not assignment:
            raise ValueError('Assignment does not exist')
        lock_flag = not assignment['active']

        # Do not allow submissions after the lock date
        elgible_submit = args['submit'] and not lock_flag
        backup = make_backup(user, assignment['id'], args[
                             'messages'], elgible_submit)
        if args['submit'] and lock_flag:
            raise ValueError('Late Submission')
        if elgible_submit and assignment['autograding_key']:
            submit_continous(backup)
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


class ScoreSchema(APISchema):

    post_fields = {
        'success': fields.Boolean,
        'message': fields.String
    }

    def __init__(self):
        APISchema.__init__(self)
        self.parser.add_argument('bid', type=str, required=True,
                                 help='ID of submission')
        self.parser.add_argument('kind', type=str, required=True,
                                 help='Kind of score')
        self.parser.add_argument('score', type=float, required=True,
                                 help='Score')
        self.parser.add_argument('message', type=str, required=True,
                                 help='Score details')

    def add_score(self, user):
        args = self.parse_args()
        backup = models.Backup.query.get(decode_id(args['bid']))
        kind = args['kind'].lower().strip()
        score, message = args['score'], args['message']
        score = make_score(user, backup, score, message, kind)
        if score:
            return {'success': True, 'message': 'OK'}
        return {'success': False, 'message': "Permission error"}

class Resource(restful.Resource):
    version = 'v3'
    method_decorators = [authenticate, check_version]
    # applies to all inherited resources

    def __repr__(self):
        return "<Resource {0}>".format(self.__class__.__name__)

    def make_response(self, data, *args, **kwargs):
        return super().make_response(data, *args, **kwargs)

    def can(self, user, course, action):
        if user.is_admin:
            return True
        return False


class PublicResource(Resource):
    method_decorators = []

class V3Info(PublicResource):
    def get(self):
        return {
            'version': API_VERSION,
            'url': '/api/{0}/'.format(API_VERSION),
            'documentation': 'http://github.com/Cal-CS-61A-Staff/ok/wiki'
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
        bid = decode_id(key)
        backup = self.model.query.filter_by(id=bid).first()
        if not backup:
            if user.is_admin:
                return restful.abort(404)
            return restful.abort(403)
        # TODO: Check if user is researcher. If so, anonmyize submitter info.
        if not self.model.can(backup, user, 'view'):
            return restful.abort(403)
        backup.group = [models.User.get_by_id(uid) for uid in backup.owners()]
        return backup

    @marshal_with(schema.post_fields)
    def post(self, user, key=None):
        if key is not None:
            restful.abort(405)
        try:
            backup = self.schema.store_backup(user)
        except ValueError as e:
            data = {'backup': True}
            if 'late' in str(e).lower():
                data['late'] = True
            return restful.abort(403, message=str(e), data=data)

        assignment = backup.assignment
        return {
            'email': current_user.email,
            'key': encode_id(backup.id),
            'url': url_for('student.code', name=assignment.name, submit=backup.submit,
                           bid=encode_id(backup.id), _external=True),
            'course': assignment.course,
            'assignment': assignment.name
        }

class ExportBackup(Resource):
    """ Export backup retreival resource without submitter information.
        Authenticated. Permissions: >= Staff
        Used by: Export Scripts.
    """
    schema = BackupSchema()
    model = models.Assignment

    @marshal_with(schema.export_list)
    def get(self, user, aid, email):
        assign = (self.model.query.filter_by(id=aid)
                      .one_or_none())
        target = models.User.lookup(email)

        limit = request.args.get('limit', 150)
        offset = request.args.get('offset', 0)

        if not assign or not target:
            if user.is_admin:
                return restful.abort(404)
            return restful.abort(403)

        if not self.model.can(assign, user, 'export'):
            return restful.abort(403)

        backups = (models.Backup.query.filter(
            models.Backup.submitter_id == target.id,
            models.Backup.assignment_id == assign.id,
        ).order_by(models.Backup.created.desc())
         .limit(limit)
         .offset(offset))

        num_backups = backups.count()
        has_more = ((num_backups - offset) - limit) > 0

        data = {'backups': backups.all(),
                'count': num_backups,
                'limit': limit,
                'offset': offset,
                'has_more':  has_more}
        return data

class ExportFinal(Resource):
    """ Export backup retreival.
        Authenticated. Permissions: >= Staff
        Used by: Export Scripts.
    """
    schema = BackupSchema()
    model = models.Assignment

    @marshal_with(schema.full_export_list)
    def get(self, user, aid):
        assign = (self.model.query.filter_by(id=aid)
                      .one_or_none())

        if not assign:
            if user.is_admin:
                return restful.abort(404)
            return restful.abort(403)

        if not self.model.can(assign, user, 'export'):
            return restful.abort(403)

        students, subms, no_subms = assign.course_submissions()

        output = []
        subm_keys = sorted(list(subms))

        for s_id in subm_keys:
            output.append(models.Backup.query.get(s_id))

        num_subms = len(output)

        for backup in output:
            backup.group = [models.User.get_by_id(uid) for uid in backup.owners()]

        data = {'backups': output,
                'count': num_subms}
        return data

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

class Score(Resource):
    """ Score creation.
        Authenticated. Permissions: >= Staff
        Used by: Autograder.
    """
    schema = ScoreSchema()
    model = models.Score

    @marshal_with(schema.post_fields)
    def post(self, user):
        score = self.schema.add_score(user)
        if not score or not score['success']:
            restful.abort(401)
        return {
            'email': current_user.email,
            'success': True
        }


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


api.add_resource(V3Info, '/v3/')
api.add_resource(Backup, '/v3/backups/', '/v3/backups/<string:key>/')
api.add_resource(ExportBackup, '/v3/assignment/<int:aid>/export/<string:email>')
api.add_resource(ExportFinal, '/v3/assignment/<int:aid>/submissions/')
api.add_resource(Enrollment, '/v3/enrollment/<string:email>/')
api.add_resource(Score, '/v3/score/')
api.add_resource(Version, '/v3/version/', '/v3/version/<string:name>')
