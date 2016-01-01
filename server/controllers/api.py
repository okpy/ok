
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


from flask import Blueprint, jsonify, request, session

import flask_restful as restful
# from flask_restful import reqparse
import datetime

from flask_restful.representations.json import output_json

from functools import wraps

from flask.ext.login import current_user
from server.auth import token_email

# from server.extensions import cache
from server.models import User

endpoints = Blueprint('api', __name__)
api = restful.Api(endpoints, catch_all_404s=True)

API_VERSION = 'v3'


@api.representation('application/json')
def api_output(data, code, headers=None):
    """ Format JSON output to match v1 API output format.
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
    """ Provide user object to API methods. Decorates all API methods.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Public methods do not need authentication
        if getattr(func, 'public', False):
            return func(*args, **kwargs)

        token = request.args.get('token', '')
        user = None
        if token:
            email = token_email(token)
            user = User.query.filter_by(email=email).first()
        elif current_user.is_authenticated:
            user = current_user

        if user:
            kwargs['user'] = user
            return func(*args, **kwargs)

        restful.abort(401)  # TODO : Custom Auth Error Message.
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


class PublicResource(Resource):
    method_decorators = [check_version]


class v3Info(Resource):
    def get(self, user):
        return {
            'version': API_VERSION,
            'url': '/api/{}/'.format(API_VERSION),
            'documentation': 'http://github.com/Cal-CS-61A-Staff/ok/wiki',
            'token': session['google_token']  # FOR TESTING ONLY
        }

#  TODO Document why there are seperate classes for Subm/Submission
#  Might decide to combine them at some point
#  Fewer methods/APIs as V1 since the frontend will not use the API


class Submission(Resource):
    """ Submission retreival resource.
        Authenticated. Permissions: >= User/Staff
        Used by: Ok Client Submission.

    """
    def get(self, user, id):
        return {'time': str(datetime.datetime.now())}


class Submissions(Resource):
    """ Submission Creation Resource.
        Authenticated. No other permissions check
    """
    def post(self, user):
        return {'id': 1}


class Backup(Resource):
    """ Submission retreival resource.
        Authenticated. Permissions: >= User/Staff
        Used by: Ok Client Submission/Exports.
    """
    def get(self, id, user):
        return {'time': str(datetime.datetime.now())}


class Backups(Resource):
    """ Backup creation resource.
        Authenticated. Permissions: >= User/Staff
        Used by: Ok Client Backup/Exports.
    """
    def post(self, user):
        return {'id': 1}


class Scores(Resource):
    """ Score creation resource.
        Authenticated. Permissions: >= Staff
        Used by: Autograder
    """
    def post(self, backup, user):
        return {'time': str(datetime.datetime.now())}


# TODO API should automatically add data, error, code (to match old interface)

api.add_resource(v3Info, '/v3')

api.add_resource(Submissions, '/v3/submission')
api.add_resource(Submission, '/v3/submission/<int:id>')

api.add_resource(Backups, '/v3/backup/')
api.add_resource(Backup, '/v3/backup/<int:id>')
api.add_resource(Scores, '/v3/backup/<int:backup>/score')
