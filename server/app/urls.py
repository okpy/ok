"""
URL dispatch route mappings and error handlers
"""
from functools import wraps
import logging
import traceback

from flask import render_template, session, request

from google.appengine.api import users
from google.appengine.ext.db import BadValueError
from google.appengine.ext import ndb

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
    params['DEBUG'] = app.config['DEBUG']
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

class WebArgsException(Exception):
    pass

@api.parser.error_handler
def args_error(error):
    raise WebArgsException(error)

def register_api(view, endpoint, url):
    """
    Registers the given view at the endpoint, accessible by the given url.
    """
    url = API_PREFIX + '/' + url
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
        except (WebArgsException, BadValueError) as e:
            message = "Invalid arguments: %s" % e.message
            logging.warning(message)
            return utils.create_api_response(400, message)
        except Exception as e: #pylint: disable=broad-except
            #TODO(martinis) add tests
            error_message = traceback.format_exc()
            logging.error(error_message)
            return utils.create_api_response(500, 'internal server error:\n%s' %
                                             error_message)

    app.add_url_rule('%s' % url, view_func=wrapped, defaults={'path': None},
            methods=['GET', 'POST'])
    app.add_url_rule('%s/<path:path>' % url, view_func=wrapped,
            methods=['GET', 'POST', 'DELETE', 'PUT'])

register_api(api.UserAPI, 'user_api', 'user')
register_api(api.AssignmentAPI, 'assignment_api', 'assignment')
register_api(api.SubmissionAPI, 'submission_api', 'submission')
register_api(api.VersionAPI, 'version_api', 'version')
register_api(api.CourseAPI, 'course_api', 'course')
