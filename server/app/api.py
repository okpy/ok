"""
The public API
"""

from flask.views import MethodView
from flask.app import request
from flask import jsonify

from app import app
from app import models

from functools import wraps

API_PREFIX = '/api/v1'

def handle_error(func):
    """Handles all errors that happen in an API request"""
    @wraps(func)
    def decorated(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            return create_response(500, 'internal server error', None)
    return decorated

class APIResource:
    """
    The base class for an API Resource
    """

    @classmethod
    def get_model(cls):
        """
        Get the model this API resource is associated with.
        Needs to be overridden by a subclass.
        """
        raise NotImplementedError

    @handle_error
    def get(self, key):
        """
        The GET HTTP method
        """
        if key is None:
            return self.index()
        obj = self.get_model().get_by_id(key)
        if not obj:
            return create_api_response(404, "{resource} {key} not found"
                                       .format(resource=self.name,
                                               key=key), None)
        return create_api_response(200, "", obj)

    @handle_error
    def put(self):
        """
        The PUT HTTP method
        """
        new_mdl = self.get_model()()
        new_mdl.put()
        return create_response(200, "model created successfully", None)

    @handle_error
    def post(self):
        """
        The POST HTTP method
        """
        post_dict = request.json
        retval, new_mdl = self.new_entity(post_dict)
        if retval:
            return create_api_response(200, "success", {
                'key': new_mdl.key
            })
        return create_api_response(500, "success", None)

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        """
        new_mdl = self.get_model().from_dict(attributes)
        new_mdl.put()
        return True, new_mdl

    @handle_error
    def delete(self, user_id):
        """
        The DELETE HTTP method
        """
        ent = self.get_model().query.get(user_id)
        ent.key.delete()
        return create_api_response(200, "success", None)

    @handle_error
    def index(self):
        """
        Index HTTP method thing.
        """
        return create_api_response(200, "success", list(self.get_model().query()))

class UserAPI(MethodView, APIResource):
    """
    The API resource for the User Object
    """
    name = "User"
    @classmethod
    def get_model(cls):
        return models.User

class AssignmentAPI(MethodView, APIResource):
    """
    The API resource for the Assignment Object
    """
    name = "Assignment"
    @classmethod
    def get_model(cls):
        return models.Assignment

class SubmissionAPI(MethodView, APIResource):
    """
    The API resource for the Submission Object
    """
    name = "Submission"
    @classmethod
    def get_model(cls):
        return models.Submission

    @handle_error
    def post(self):
        post_dict = request.json

        project_name = post_dict.pop('project_name', None)
        if not project_name:
            return create_api_response(400, "project name needs to be specified", None)
        project = models.Assignment.query().filter(
            models.Assignment.name == project_name).all()
        if len(project) == 0:
            return create_api_response(500, "project name doesn't exist", None)
        if len(project) != 1:
            return create_api_response(500, "more than one project with given name exist", None)
        retval, new_mdl = self.new_entity(post_dict)
        if retval:
            return create_api_response(200, 'success', {
                'key': new_mdl.key
            })


def register_api(view, endpoint, url, primary_key='key', pk_type='int'):
    """
    Registers the given view at the endpoint, accessible by the given url.
    """
    url = API_PREFIX + url
    view_func = view.as_view(endpoint)
    app.add_url_rule(url, defaults={primary_key: None},
                     view_func=view_func, methods=['GET',])
    app.add_url_rule("%s/" % url, defaults={primary_key: None},
                     view_func=view_func, methods=['GET',])
    app.add_url_rule('%s/' % url, view_func=view_func, methods=['POST',])
    app.add_url_rule('%s/<%s:%s>' % (url, pk_type, primary_key),
                     view_func=view_func, methods=['GET', 'PUT', 'DELETE'])

def create_api_response(status, message, data):
    """Creates a JSON response that contains status code (HTTP),
    an arbitrary message string, and a dictionary or list of data"""
    response = jsonify(**{
        'status': status,
        'message': message,
        'data': data
    })
    response.status_code = status
    return response

register_api(UserAPI, 'user_api', '/user')
register_api(AssignmentAPI, 'assignment_api', '/assignment')
register_api(SubmissionAPI, 'submission_api', '/submission')
