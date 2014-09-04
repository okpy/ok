"""
URL dispatch route mappings and error handlers
"""
from functools import wraps
import logging
import traceback

from flask import render_template, session, request

from google.appengine.api import users

from app import app
from app import api
from app import auth
from app import models
from app import utils
from app.constants import API_PREFIX

@app.route("/")
def index():
    user = users.get_current_user()
    params = {}
    if user is None:
        params['users_link'] = users.create_login_url('/')
        params['users_title'] = "Sign In"
    else:
        logging.info("User is %s." % user.email())
        params["user"] = {'email': user.email()}
        params['users_link'] = users.create_logout_url('/')
        params['users_title'] = "Log Out"
    return render_template("base.html", **params)

## Error handlers
# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', error=e), 404

# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('base.html', error=e), 500

def register_api(view, endpoint, url, primary_key='key', pk_type='int:'):
    """
    Registers the given view at the endpoint, accessible by the given url.
    """
    url = API_PREFIX + url
    view = view.as_view(endpoint)

    @wraps(view)
    def wrapped(*args, **kwds):
        #TODO(martinis) add tests
        if 'client_version' in request.args:
            if request.args['client_version'] != app.config['CLIENT_VERSION']:
                return utils.create_api_response(403, "incorrect client version", {
                    'supplied_version': request.args['client_version'],
                    'correct_version': app.config['CLIENT_VERSION']
                })

        user = auth.authenticate()
        if not isinstance(user, models.User):
            return user
        session['user'] = user

        try:
            return view(*args, **kwds)
        except Exception: #pylint: disable=broad-except
            #TODO(martinis) add tests
            error_message = traceback.format_exc()
            logging.error(error_message)
            return utils.create_api_response(500, 'internal server error:\n%s' %
                                             error_message)

    # To get all objects
    app.add_url_rule(url, defaults={primary_key: None},
                     view_func=wrapped, methods=['GET', ])

    # To create a new object
    app.add_url_rule(url, view_func=wrapped, methods=['POST', ])

    # To operate on individual object
    app.add_url_rule('%s/<%s%s>' % (url, pk_type, primary_key),
                     view_func=wrapped, methods=['GET', 'PUT', 'DELETE'])

register_api(api.UserAPI, 'user_api', '/user', pk_type='')
register_api(api.AssignmentAPI, 'assignment_api', '/assignment')
register_api(api.SubmissionAPI, 'submission_api', '/submission')
register_api(api.VersionAPI, 'version_api', '/version')
register_api(api.CourseAPI, 'course_api', '/course')

