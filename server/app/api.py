"""
The public API
"""

from flask.views import MethodView
from flask import jsonify, request

from google.appengine.api import users

from app import app
from app import models
from app.models import BadValueError

from functools import wraps
import traceback

API_PREFIX = '/api/v1'


def handle_error(func):
    """Handles all errors that happen in an API request"""
    @wraps(func)
    def decorated(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception: #pylint: disable=broad-except
            error_message = traceback.format_exc()
            return create_api_response(500, 'internal server error:\n%s' %
                                       error_message)
    return decorated


class APIResource(object):
    """The base class for API resources.

    Set the name and get_model for each subclass.
    """
    name = "BASE API RESOURCE"

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
                                               key=key))
        return create_api_response(200, "", obj)

    @handle_error
    def put(self):
        """
        The PUT HTTP method
        """
        new_mdl = self.get_model()()
        new_mdl.put()
        return create_api_response(200, "success")

    @handle_error
    def post(self):
        """
        The POST HTTP method
        """
        form = self.get_model().new_form()
        if not form.validate_on_submit():
            return create_api_response(400, str(form.errors))
        retval, new_mdl = self.new_entity(form)
        if retval:
            return create_api_response(200, "success", {
                'key': new_mdl.key
            })
        return create_api_response(500, "could not create resource")

    def new_entity(self, form):
        """
        Creates a new entity with given attributes.
        """
        new_mdl = self.get_model()()
        form.populate_obj(new_mdl)
        new_mdl.put()
        return True, new_mdl

    @handle_error
    def delete(self, user_id):
        """
        The DELETE HTTP method
        """
        ent = self.get_model().query.get(user_id)
        ent.key.delete()
        return create_api_response(200, "success")

    @handle_error
    def index(self):
        """
        Index HTTP method thing.
        """
        return create_api_response(
            200, "success", list(self.get_model().query()))


class UserAPI(MethodView, APIResource):
    """The API resource for the User Object"""
    name = "User"

    @classmethod
    def get_model(cls):
        return models.User


class AssignmentAPI(MethodView, APIResource):
    """The API resource for the Assignment Object"""
    name = "Assignment"

    @classmethod
    def get_model(cls):
        return models.Assignment


class SubmitNDBImplementation:
    """Implementation of DB calls required by submission using Google NDB"""

    def lookup_assignments_by_name(self, name):
        """Look up all assignments of a given name."""
        by_name = models.Assignment.name == name
        return list(models.Assignment.query().filter(by_name))

    def create_submission(self, user, assignment, messages):
        """Create submission using user as parent to ensure ordering."""
        submission =  models.Submission(submitter=user,
                                        assignment=assignment,
                                        messages=messages)
        submission.put()
        return submission


class SubmissionAPI(MethodView, APIResource):
    """The API resource for the Submission Object"""
    name = "Submission"
    db = SubmitNDBImplementation()
    post_fields = ['access_token', 'assignment', 'messages', 'submitter']

    @classmethod
    def get_model(cls):
        return models.Submission

    def get_assignment(self, name):
        """Look up an assignment by name or raise a validation error."""
        assignments = self.db.lookup_assignments_by_name(name)
        if not assignments:
            raise BadValueError('Assignment \'%s\' not found' % name)
        if len(assignments) > 1:
            raise BadValueError('Multiple assignments named \'%s\'' % name)
        return assignments[0]

    def submit(self, user, assignment, messages):
        """Process submission messages for an assignment from a user."""
        valid_assignment = self.get_assignment(assignment)
        submission = self.db.create_submission(user, valid_assignment, messages)
        return create_api_response(200, "success", {
            'key': submission.key.id()
        })

    @handle_error
    def post(self):
        for key in request.json:
            if key not in self.post_fields:
                return create_api_response(400, 'Unknown field %s' % key)
        for field in self.post_fields:
            if field not in request.json:
                return create_api_response(400,
                                           'Missing required field %s' % field)

        # TODO(denero) Fix user plumbing using @requires_authenticated_user
        #              and change to self.submit(**request.json)
        user = users.get_current_user()
        try:
            return self.submit(user, request.json['assignment'], 
                               request.json['messages'])
        except BadValueError as e:
            return create_api_response(400, e.message)


def register_api(view, endpoint, url, primary_key='key', pk_type='int'):
    """
    Registers the given view at the endpoint, accessible by the given url.
    """
    url = API_PREFIX + url
    view_func = view.as_view(endpoint)
    app.add_url_rule(url, defaults={primary_key: None},
                     view_func=view_func, methods=['GET', ])
    app.add_url_rule('%s/new' % url, view_func=view_func, methods=['POST', ])
    app.add_url_rule('%s/<%s:%s>' % (url, pk_type, primary_key),
                     view_func=view_func, methods=['GET', 'PUT', 'DELETE'])


def create_api_response(status, message, data=None):
    """Creates a JSON response that contains status code (HTTP),
    an arbitrary message string, and a dictionary or list of data"""
    response = jsonify(**{
        'status': status,
        'message': message,
        'data': data
    })
    response.status_code = status
    return response

# TODO(denero) Add appropriate authentication requirements
register_api(UserAPI, 'user_api', '/user')
register_api(AssignmentAPI, 'assignment_api', '/assignment')
register_api(SubmissionAPI, 'submission_api', '/submission')
