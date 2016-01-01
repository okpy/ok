
"""
API.py - /api/{version}/endpoints

    Primarily for OK Client & some frontend features
    Example of defining a new API:

    class UserAPI(Resource):
        def get(self, user):
            return {'id': user.id}

    api.add_resource(UserAPI, '/v3/user')
"""


from flask import Blueprint, jsonify
import flask_restful as restful
from flask_restful.representations.json import output_json

from functools import wraps

from flask.ext.login import current_user
from server.auth import GoogleAuthenticator

# from server.extensions import cache
from server.models import User

endpoints = Blueprint('api', __name__)
api = restful.Api(endpoints, catch_all_404s=True)

API_VERSION = 'v3'

from flask_restful import reqparse


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

default_parser = reqparse.RequestParser()
default_parser.add_argument('token', type=str, help='User Authentication')
default_parser.add_argument('client_version', type=str)


def authenticate(func):
    """ Provide user object to API methods. Decorates all API methods.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Public methods do not need authentication
        if getattr(func, 'public', False):
            return func(*args, **kwargs)

        default_args = default_parser.parse_args()

        user = None
        if current_user.is_authenticated():
            user = current_user
        elif args['token']:
            email = GoogleAuthenticator.email(default_args['token'])
            user = User.query.filter_by(email=email).first()

        if user:
            kwargs['user'] = user
            return func(*args, **kwargs)

        restful.abort(401)  # TODO : Custom Auth Error Message.
    return wrapper


def check_version(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        default_args = default_parser.parse_args()
        supplied = default_args['client_version']
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


class v3InfoAPI(PublicResource):
    def get(self):
        return {
            'version': '3',
            'url': '/api/v3/',
            'documentation': 'http://github.com/Cal-CS-61A-Staff/ok/wiki'
        }


# TODO API should automatically add data, error, code (to match old interface)

api.add_resource(v3InfoAPI, '/v3')
