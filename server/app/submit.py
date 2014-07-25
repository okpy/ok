"""Public client API for submission."""

from flask.views import MethodView
from flask.app import request
from flask import json

from google.appengine.api import users

from app import app
from app.decorators import login_required
from models import BadValueError
from submit_ndb import lookup_assignments_by_name, create_submission

SUBMIT_PREFIX = '/v1'


def _lookup_assignment(name):
    """Look up an assignment by name or raise a validation error."""
    if not name:
        raise BadValueError('No assignment name provided')
    assignments = lookup_assignments_by_name(name)
    if not assignments:
        raise BadValueError('Assignment "%s" not found' % name)
    if len(assignments) > 1:
        raise BadValueError('Multiple assignments named "%s"' % name)
    return assignments[0]


def _get_user():
    """Look up current user."""
    user = users.get_current_user()
    if not user:
        raise BadValueError('User unknown')
    return user


def _error_response(exception):
    """Respond with a descriptive error for an exception."""
    return json.dumps({'message': str(exception)}), 500


class Submit(MethodView):
    """Submit an assignment revision via a post request."""

    def post(self):
        # Each submission requires an authenticated user, an assignment name,
        # and the contents of various protocols.
        post_data = dict(request.json)
        try:
            assignment = _lookup_assignment(post_data['assignment'])
            user = _get_user()
            messages = post_data['messages']
            # TODO(denero) Parse other protocols than file_contents
            contents = messages['file_contents']
            submission = create_submission(user, assignment, contents)
            submission.put()
            return json.dumps({'status': 200})
        except (BadValueError, KeyError) as e:
            return _error_response(e)


def register(view, endpoint, url):
    """Register the Submit API."""
    url = SUBMIT_PREFIX + url
    view_func = login_required(view.as_view(endpoint))
    app.add_url_rule(url, view_func=view_func, methods=['POST'])

register(Submit, 'submit_api', '/submit')

