"""
The public API
"""

from flask.views import MethodView
from flask.app import request

from app import app
from app import models
from app.models import BadValueError
from app.constants import API_PREFIX
from app.utils import create_api_response
from app.auth import requires_authenticated_user
from app.decorators import handle_error


class APIResource(object):
    """The base class for API resources.

    Set the name and get_model for each subclass.
    """
    name = None

    @classmethod
    def get_model(cls):
        """
        Get the model this API resource is associated with.
        Needs to be overridden by a subclass.
        """
        raise NotImplementedError

    @handle_error
    def get(self, key, user=None):
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
    def put(self, user=None):
        """
        The PUT HTTP method
        """
        new_mdl = self.get_model()()
        new_mdl.put()
        return create_api_response(200, "success")

    @handle_error
    def post(self, user=None):
        """
        The POST HTTP method
        """
        post_dict = request.json
        assert request.json
        retval, new_mdl = self.new_entity(post_dict)
        if retval:
            return create_api_response(200, "success", {
                'key': new_mdl.key
            })
        return create_api_response(500, "could not create resource")

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        """
        new_mdl = self.get_model().from_dict(attributes)
        new_mdl.put()
        return True, new_mdl

    @handle_error
    def delete(self, user_id, user=None):
        """
        The DELETE HTTP method
        """
        ent = self.get_model().query.get(user_id)
        ent.key.delete()
        return create_api_response(200, "success")

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
    post_fields = ['assignment', 'messages']

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
    def post(self, user=None):
        for key in request.json:
            if key not in self.post_fields:
                return create_api_response(400, 'Unknown field %s' % key)
        for field in self.post_fields:
            if field not in request.json:
                return create_api_response(400,
                                           'Missing required field %s' % field)

        try:
            return self.submit(user, request.json['assignment'],
                               request.json['messages'])
        except BadValueError as e:
            return create_api_response(400, e.message)

    @handle_error
    def get(self, key, user=None):
        """
        The GET HTTP method
        """
        if key is None:
            return self.index(user)
        obj = self.get_model().get_by_id(key)
        if not obj:
            return create_api_response(404, "{resource} {key} not found"
                                       .format(resource=self.name,
                                               key=key))
        if not obj.submitter:
            return create_api_response(400, "user for submission doesn't exist")
        return create_api_response(200, "", obj)

    def index(self, user):
        """
        Index HTTP method thing.
        """
        return create_api_response(
            200, "success", list(self.get_model().query(self.get_model().submitter.email == user.email)))

def register_api(view, endpoint, url, primary_key='key', pk_type='int', admin=False):
    """
    Registers the given view at the endpoint, accessible by the given url.
    """
    url = API_PREFIX + url
    view_func = requires_authenticated_user(admin=admin)(view.as_view(endpoint))
    app.add_url_rule(url, defaults={primary_key: None},
                     view_func=view_func, methods=['GET', ])
    app.add_url_rule('%s/new' % url, view_func=view_func, methods=['POST', ])
    app.add_url_rule('%s/<%s:%s>' % (url, pk_type, primary_key),
                     view_func=view_func, methods=['GET', 'PUT', 'DELETE'])

# TODO(denero) Add appropriate authentication requirements
register_api(UserAPI, 'user_api', '/user', admin=True)
register_api(AssignmentAPI, 'assignment_api', '/assignment', admin=True)
register_api(SubmissionAPI, 'submission_api', '/submission')
