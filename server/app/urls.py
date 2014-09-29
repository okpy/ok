"""
URL dispatch route mappings and error handlers
"""
from functools import wraps
import logging
import traceback
import collections

from flask import render_template, session, request, Response

from google.appengine.api import users

from app import app
from app import api
from app import auth
from app import models
from app import utils
from app.constants import API_PREFIX
from app.exceptions import *

@app.route("/")
def index():
    user = users.get_current_user()
    params = {}
    if user is None:
        params['users_link'] = users.create_login_url('/')
        params['users_title'] = "Sign In"
    else:
        logging.info("User is %s", user.email())
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

@api.parser.error_handler
def args_error(e):
    raise BadValueError(e.message)

def check_version(client):
    latest = models.Version.query(models.Version.name=='okpy').get()

    if latest is None or latest.current_version is None:
        raise APIException('Current version of okpy not found')
    latest = latest.current_version

    # If it returned a response, and not a string
    if not isinstance(latest, (str, unicode)):
        raise RuntimeError(latest)
    if client != latest:
        raise IncorrectVersionError(client, latest)


def register_api(view, endpoint, url):
    """
    Registers the given view at the endpoint, accessible by the given url.
    """
    url = '/'.join((API_PREFIX, view.api_version, url))
    view = view.as_view(endpoint)

    @wraps(view)
    def api_wrapper(*args, **kwds):
        #TODO(martinis) add tests
        # Any client can check for the latest version

        try:
            request.fields = {}
            message = "success"
            if request.args.get('client_version'):
                check_version(request.args['client_version'])

            user = auth.authenticate()
            if not isinstance(user, models.User):
                return user
            session['user'] = user
            logging.info("User is %s.", user.email)

            rval = view(*args, **kwds)

            if isinstance(rval, list):
                rval = utils.create_api_response(200, message, rval)
            elif (isinstance(rval, collections.Iterable)
                  and not isinstance(rval, dict)):
                rval = utils.create_api_response(*rval)
            elif isinstance(rval, Response):
                pass
            else:
                rval = utils.create_api_response(200, message, rval)

            return rval
        except APIException as e:
            logging.exception(e.message)
            return utils.create_api_response(e.code, e.message, e.data)
        except Exception as e: #pylint: disable=broad-except
            logging.exception(e.message)
            return utils.create_api_response(500, 'internal server error :(')

    app.add_url_rule('%s' % url, view_func=api_wrapper, defaults={'path': None},
            methods=['GET', 'POST'])
    app.add_url_rule('%s/<path:path>' % url, view_func=api_wrapper,
            methods=['GET', 'POST', 'DELETE', 'PUT'])

register_api(api.AssignmentAPI, 'assignment_api', 'assignment')
register_api(api.SubmissionAPI, 'submission_api', 'submission')
register_api(api.VersionAPI, 'version_api', 'version')
register_api(api.CourseAPI, 'course_api', 'course')
register_api(api.GroupAPI, 'group_api', 'group')
register_api(api.UserAPI, 'user_api', 'user')
