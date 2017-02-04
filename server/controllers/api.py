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
from server.constants import STAFF_ROLES, VALID_ROLES

endpoints = Blueprint('api', __name__)
endpoints.config = {}


@endpoints.record
def record_params(setup_state):
    """ Load used app configs into local config on registration from
    server/__init__.py """
    app = setup_state.app
    endpoints.config['tz'] = app.config.get('TIMEZONE', 'utc')  # sample config
    endpoints.config['debug'] = app.debug


api = restful.Api(endpoints)

API_VERSION = 'v3'

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

def custom_abort(status_code, message, data=None):
    response = jsonify({
        'code': status_code,
        'data': data,
        'message': message,
    })
    response.status_code = status_code
    return response

##############
# Decorators #
##############

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


def check_scopes(func):
    """ Check scopes for route against user scopes (if using OAuth)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if getattr(func, 'public', False):
            return func(*args, **kwargs)
        user_scopes = getattr(current_user, 'scopes', None)
        resource = getattr(func, '__self__', None)
        if not resource:
            # Not protecting an API resource, unknown permissions
            return func(*args, **kwargs)
        resource_scopes = getattr(resource, 'required_scopes', {})
        # If unspecified, assume 'all' scope is neccesary
        needed_scopes = resource_scopes.get(func.__name__, ['all'])
        if user_scopes is None:
            # Not an OAuth Based Request
            return func(*args, **kwargs)
        else:
            if 'all' not in user_scopes:
                for scope in needed_scopes:
                    if scope not in user_scopes:
                        data = {'current_scopes': user_scopes, 'required_scopes': needed_scopes}
                        return custom_abort(403,
                                            "The '{}' scope is required".format(scope),
                                            data=data)
        return func(*args, **kwargs)
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

    score = models.Score(grader_id=user.id, assignment=backup.assignment,
                         backup=backup, user_id=backup.submitter_id,
                         score=score, message=message, kind=kind)
    models.db.session.add(score)
    models.db.session.commit()
    score.archive_duplicates()
    return score

###########
# Schemas #
###########

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
        'timezone': fields.String
    }

class ParticipationSchema(APISchema):
    get_fields = {
        'course_id': fields.Integer,
        'role': fields.String,
        'course': fields.Nested(CourseSchema.get_fields),
        'class_account': fields.String,
        'section': fields.String,
    }

class EnrollmentSchema(APISchema):
    get_fields = {
        'courses': fields.List(fields.Nested(ParticipationSchema.get_fields))
    }

class FileSchema(APISchema):
    get_fields = {
        'id': HashIDField,
        'mimetype': fields.String,
        'download_link': fields.String,
        'filename': fields.String
    }

class UserSchema(APISchema):
    get_fields = {
        'id': HashIDField,
        'email': fields.String,
        'name': fields.String,
        'is_admin': fields.Boolean,
        'participations': fields.List(fields.Nested(ParticipationSchema.get_fields))
    }

    simple_fields = {
        'id': HashIDField,
        'email': fields.String,
    }

class AssignmentSchema(APISchema):
    get_fields = {
        'due_date': fields.DateTime(dt_format='iso8601'),
        'lock_date': fields.DateTime(dt_format='iso8601'),
        'display_name': fields.String,
        'name': fields.String,
        'max_group_size': fields.Integer,
        'url': fields.String,
        'course': fields.Nested(CourseSchema.get_fields),
        'files': fields.Raw
    }

    list_fields = {
        'due_date': fields.DateTime(dt_format='iso8601'),
        'lock_date': fields.DateTime(dt_format='iso8601'),
        'display_name': fields.String,
        'name': fields.String,
        'max_group_size': fields.Integer,
        'url': fields.String,
        'active': fields.String
    }

    simple_fields = {
        'course': fields.Nested(CourseSchema.get_fields),
        'name': fields.String,
    }

class CourseAssignmentSchema(APISchema):
    get_fields = {'assignments':
                  fields.List(fields.Nested(AssignmentSchema.list_fields))}

class CourseEnrollmentSchema(APISchema):
    get_fields = {role: fields.List(fields.Nested(UserSchema.simple_fields))
                  for role in VALID_ROLES}


class GroupSchema(APISchema):
    member_fields = {
        'status': fields.String,
        'user': fields.Nested(UserSchema.simple_fields),
        'updated': fields.DateTime(dt_format='iso8601'),
        'created': fields.DateTime(dt_format='iso8601'),
    }
    get_fields = {
        'members': fields.List(fields.Nested(member_fields)),
    }


class BackupSchema(APISchema):
    get_fields = {
        'id': HashIDField,  # Use Hash ID
        'submitter': fields.Nested(UserSchema.simple_fields),
        'assignment': fields.Nested(AssignmentSchema.simple_fields),
        'messages': fields.List(fields.Nested(MessageSchema.get_fields)),
        'created': fields.DateTime(dt_format='iso8601'),
        'submission_time': fields.DateTime(dt_format='iso8601'),
        'is_late': fields.Boolean,
        'submit': fields.Boolean,
        'external_files': fields.List(fields.Nested(FileSchema.get_fields)),
        'group': fields.List(fields.Nested(UserSchema.simple_fields)),
    }

    export_fields = {
        'id': HashIDField,
        'messages': fields.List(fields.Nested(MessageSchema.get_fields)),
        'external_files': fields.List(fields.Nested(FileSchema.get_fields)),
        'created': fields.DateTime(dt_format='iso8601'),
        'submission_time': fields.DateTime(dt_format='iso8601'),
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
        backup = make_backup(user, assignment['id'], args['messages'],
                             elgible_submit)
        if args['submit'] and lock_flag:
            raise ValueError('Late Submission of {}'.format(args['assignment']))
        if elgible_submit and assignment['autograding_key']:
            submit_continous(backup)
        return backup


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
        try:
            bid = decode_id(args['bid'])
        except (ValueError, TypeError):
            restful.abort(404)
        backup = models.Backup.query.get(bid)
        kind = args['kind'].lower().strip()
        score, message = args['score'], args['message']
        score = make_score(user, backup, score, message, kind)
        if score:
            return {'success': True, 'message': 'OK'}
        return {'success': False, 'message': "Permission error"}

class CommentSchema(APISchema):
    post_fields = {}

    def __init__(self):
        APISchema.__init__(self)
        self.parser.add_argument('filename', type=str, required=True,
                                 help='Filename to leave comment on')
        self.parser.add_argument('line', type=int, required=True,
                                 help='Line to leave comment on')
        self.parser.add_argument('message', type=str, required=True,
                                 help='Comment contents')

    def store_comment(self, user, backup):
        args = self.parse_args()
        message = args['message']
        comment = models.Comment(
            backup_id=backup.id,
            author_id=user.id,
            filename=args['filename'],
            line=args['line'],
            message=message)
        models.db.session.add(comment)
        models.db.session.commit()
        return {}


class Resource(restful.Resource):
    version = 'v3'
    method_decorators = [check_scopes, authenticate]
    required_scopes = {}
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
            'documentation': 'https://okpy.github.io/documentation',
            'github': 'https://github.com/Cal-CS-61A-Staff/ok'
        }


# TODO: should be two classes, one for /backups/ and one for /backups/<int:key>/
class Backup(Resource):
    """ Submission creation/retrieval resource.
        Authenticated. Permissions: >= User/Staff
        Used by: Ok Client, Submission/Exports, Autograder
    """
    schema = BackupSchema()
    model = models.Backup

    @marshal_with(schema.get_fields)
    def get(self, user, key=None):
        if key is None:
            restful.abort(405)
        try:
            bid = decode_id(key)
        except (ValueError, TypeError):
            restful.abort(404)

        backup = self.model.query.filter_by(id=bid).first()
        if not backup:
            if user.is_admin:
                return restful.abort(404)
            return restful.abort(403)
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
                           bid=backup.id, _external=True),
            'course': assignment.course,
            'assignment': assignment.name
        }


class Revision(Resource):
    """ Like Backup, but creates composition revisions backups after the deadline.
        Authenticated. Permissions: >= User/Staff
        Used by: Ok Client Submission/Exports.
    """
    schema = BackupSchema()
    model = models.Backup

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

        # Only accept revision if the assignment has revisions enabled
        if not assignment.revisions_allowed:
            return restful.abort(403,
                                 message=("Revisions are not enabled for {}"
                                          .format(assignment.name)),
                                 data={'backup': True, 'late': True})

        # Only accept revision if the user has a FS
        group = assignment.active_user_ids(user.id)
        fs = assignment.final_submission(group)

        if not fs:
            return restful.abort(403, message="No Submission to Revise", data={})

        # Get previous revision, (There should only be one)
        previous_revision = assignment.revision(group)
        if previous_revision:
            for score in previous_revision.scores:
                if score.kind == "revision":
                    score.archive()
        models.db.session.commit()
        fs_url = url_for('student.code', name=assignment.name, submit=fs.submit,
                         bid=fs.id, _external=True)

        assignment_creator = models.User.get_by_id(assignment.creator_id)

        make_score(assignment_creator, backup, 2.0, "Revision for {}".format(fs_url),
                   "revision")
        backup_url = url_for('student.code', name=assignment.name, submit=backup.submit,
                             bid=backup.id, _external=True)

        return {
            'email': current_user.email,
            'key': encode_id(backup.id),
            'url': backup_url,
            'course': assignment.course,
            'assignment': assignment.name,
        }


class ExportBackup(Resource):
    """ Export backup retreival resource without submitter information.
        Authenticated. Permissions: >= Staff
        Used by: Export Scripts.
    """
    schema = BackupSchema()
    model = models.Assignment

    @marshal_with(schema.export_list)
    def get(self, user, name, email):
        assign = models.Assignment.by_name(name)
        target = models.User.lookup(email)

        limit = request.args.get('limit', 150, type=int)
        offset = request.args.get('offset', 0, type=int)

        if not assign or not target:
            if user.is_admin:
                return restful.abort(404)
            return restful.abort(403)

        if not self.model.can(assign, user, 'export'):
            return restful.abort(403)

        base_query = (models.Backup.query.filter(
            models.Backup.submitter_id == target.id,
            models.Backup.assignment_id == assign.id,
        ).order_by(models.Backup.created.desc()))

        backups = base_query.limit(limit).offset(offset)

        num_backups = base_query.count()
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
    def get(self, user, name):
        assign = models.Assignment.by_name(name)

        if not assign:
            if user.is_admin:
                return restful.abort(404)
            return restful.abort(403)

        limit = request.args.get('limit', 150, type=int)
        offset = request.args.get('offset', 0, type=int)

        if not self.model.can(assign, user, 'export'):
            return restful.abort(403)

        subms = assign.course_submissions(include_empty=False)

        output = []
        subm_keys = set(s['backup']['id'] for s in subms)
        joined = models.db.joinedload
        base_query = (models.Backup.query.options(joined('assignment'),
                                                  joined('submitter'),
                                                  joined('messages'))
                            .filter(models.Backup.id.in_(subm_keys))
                            .order_by(models.Backup.created.desc()))

        num_subms = len(subm_keys)
        output = base_query.limit(limit).offset(offset)
        has_more = ((num_subms - offset) - limit) > 0

        results = []
        for backup in output:
            data = backup.as_dict()
            data.update({
                'group': [models.User.get_by_id(uid) for uid in backup.owners()],
                'assignment': assign,
                'is_late': backup.is_late,
                'submitter': backup.submitter,
                'messages': backup.messages
            })
            results.append(data)

        return {'backups': results,
                'limit': limit,
                'offset': offset,
                'count': num_subms,
                'has_more': has_more}

class Enrollment(Resource):
    """ View what courses an email is enrolled in.
        Authenticated. Permissions: >= User or admins.
        Used by: Ok Client Auth

        TODO: Make ok-client use user API instead.
        Display course level enrollment here.
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

class CourseEnrollment(Resource):
    """ Information about all students in a course.
    Authenticated. Permissions: >= User or admins
    Used by: Export scripts.
    """
    model = models.Course
    schema = CourseEnrollmentSchema()

    @marshal_with(schema.get_fields)
    def get(self, offering, user):
        course = self.model.by_name(offering)
        if course is None:
            restful.abort(404)
        if not self.model.can(course, user, 'staff'):
            restful.abort(403)
        data = {}
        for role in VALID_ROLES:
            data[role] = []
        for p in course.participations:
            data[p.role].append(p.user)
        return data

class CourseAssignment(PublicResource):
    """ All assignments for a course.
    Not authenticated. Permissions: Global
    """
    model = models.Course
    schema = CourseAssignmentSchema()

    @marshal_with(schema.get_fields)
    def get(self, offering):
        course = self.model.by_name(offering)
        if course is None:
            restful.abort(404)
        return {'assignments': course.assignments}

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
    required_scopes = {
        'get': []
    }

    @marshal_with(schema.get_fields)
    @cache.memoize(600)
    def get(self, name=None):
        if name:
            versions = self.model.query.filter_by(name=name).all()
        else:
            versions = self.model.query.all()
        return {'results': versions}

class Assignment(Resource):
    """ Infromation about an assignment
    Authenticated. Permissions: >= User
    Used by: Collaboration/Scripts
    """
    model = models.Assignment
    schema = AssignmentSchema()
    required_scopes = {
        'get': []
    }

    @marshal_with(schema.get_fields)
    def get(self, user, name):
        assign = self.model.by_name(name)
        if not assign:
            restful.abort(404)
        elif not self.model.can(assign, user, 'view'):
            restful.abort(403)
        return assign

class Group(Resource):
    """ Infromation about a group member by email.
    Authenticated. Permissions: >= User
    Used by: Collaboration/Scripts
    """
    model = models.Group
    schema = GroupSchema()

    @marshal_with(schema.get_fields)
    def get(self, user, name, email):
        assign = models.Assignment.by_name(name)
        target = models.User.lookup(email)
        default_value = {'members': []}

        if not assign:
            restful.abort(404)
        elif not target and user.is_admin:
            restful.abort(404)
        elif not target:
            restful.abort(403)

        group = self.model.lookup(target, assign)

        member_emails = [email.lower()]
        if group:
            member_emails = [m.user.email.lower() for m in group.members]

        is_member = user.email.lower() in member_emails
        is_staff = user.is_enrolled(assign.course.id, STAFF_ROLES)

        if is_member or is_staff or user.is_admin:
            if group:
                return group
            else:
                return default_value
        restful.abort(403)

class User(Resource):
    """ Infromation about the current user.
    Authenticated. Permissions: >= User
    Only admins can view other users

    Used by: External tools for auth info
    """
    model = models.User
    schema = UserSchema()
    required_scopes = {
        'get': ['email']
    }

    @marshal_with(schema.get_fields)
    def get(self, user, email=None):
        target = self.model.lookup(email)

        if not email or email.lower() == user.email.lower():
            # Get the current user
            return user

        if not target and user.is_admin:
            restful.abort(404)
        elif not target:
            restful.abort(403)

        if user.is_admin:
            return target

        restful.abort(403)

class Comment(Resource):
    """ Create comments programatically.
        Authenticated. Permissions: >= Student/Staff
        Used by: Third Party Composition Review
    """
    schema = CommentSchema()
    model = models.Comment

    @marshal_with(schema.post_fields)
    def post(self, user, backup_id):
        backup = models.Backup.query.get(backup_id)
        if not backup:
            if user.is_admin:
                restful.abort(404)
            else:
                restful.abort(403)
        if not models.Backup.can(backup, user, "view"):
            restful.abort(403)
        if not self.model.can(None, user, "create"):
            restful.abort(403)

        return self.schema.store_comment(user, backup)

# Endpoints
api.add_resource(V3Info, '/v3/')

# Submission endpoints
api.add_resource(Backup, '/v3/backups/', '/v3/backups/<string:key>/')
api.add_resource(Revision, '/v3/revision/')

# Backup Actions
api.add_resource(Comment, '/v3/backups/<hashid:backup_id>/comment/')

# Assignment Info
ASSIGNMENT_BASE = '/v3/assignment/<assignment_name:name>'
api.add_resource(Assignment, ASSIGNMENT_BASE)
api.add_resource(Group, ASSIGNMENT_BASE + '/group/<string:email>')
api.add_resource(ExportBackup, ASSIGNMENT_BASE + '/export/<string:email>')
api.add_resource(ExportFinal, ASSIGNMENT_BASE + '/submissions/')

# Course Info
COURSE_BASE = '/v3/course/<offering:offering>'
api.add_resource(CourseEnrollment, COURSE_BASE + '/enrollment')
api.add_resource(CourseAssignment, COURSE_BASE + '/assignments')

# Other
api.add_resource(Enrollment, '/v3/enrollment/<string:email>/')
api.add_resource(Score, '/v3/score/')
api.add_resource(User, '/v3/user/', '/v3/user/<string:email>')
api.add_resource(Version, '/v3/version/', '/v3/version/<string:name>')
