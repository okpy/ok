"""
URL dispatch route mappings and error handlers
"""
from functools import wraps
import logging
import traceback
import collections

import werkzeug
from flask import render_template, session, request, Response, redirect, url_for

from google.appengine.api import users
from google.appengine.ext import deferred

from app import app
from app import api
from app import auth
from app import models
from app import utils
from app.constants import API_PREFIX
from app.exceptions import *

def force_account_chooser(url):
    """Forces the user to choose a particular email account rather than assuming a default."""
    if 'ServiceLogin' in url:
        return url.replace('ServiceLogin', 'AccountChooser')
    return url

@app.route("/")
def home():
    user = users.get_current_user()
    params = {}
    if user is None:
      return redirect(url_for('landing'))
    else:
        logging.info("User is %s", user.email())
        params["user"] = {'id': user.user_id(), 'email' : user.email()}
        params['users_link'] = users.create_logout_url('/landing')
        params['users_title'] = "Log Out"
        params['relogin_link'] = users.create_logout_url(
            force_account_chooser(users.create_login_url('/')))
    params['DEBUG'] = app.config['DEBUG']
    return render_template("student.html", **params)

@app.route("/landing")
def landing():
    user = users.get_current_user()
    params = {}
    if user is None:
        params['users_link'] = force_account_chooser(
            users.create_login_url('/'))
        params['users_title'] = "Sign In"
    else:
        logging.info("User is %s", user.email())
        params["user"] = {'id': user.user_id(), 'email' : user.email()}
        params['users_link'] = users.create_logout_url('/landing')
        params['users_title'] = "Log Out"
        params['relogin_link'] = users.create_logout_url(
            force_account_chooser(users.create_login_url('/')))
    params['DEBUG'] = app.config['DEBUG']
    return render_template("landing.html", **params)


@app.route("/sudo/su/<su_email>")
def sudo(su_email):
    user = users.get_current_user()
    params = {}
    if user is not None:
        logging.info("Staff Login Attempt from %s, Attempting to login as %s", user.email(), su_email)
        userobj = models.User.lookup(user.email())
        if userobj.is_admin:
          logging.info("Sudo %s to %s granted", user.email(), su_email)
          substitute = models.User.lookup(su_email)
          if substitute:
            params["user"] = {'id': substitute.key, 'email' : substitute.email[0]}
            params["sudo"] = {'su': substitute.email[0], 'admin': user.email()}
            params['users_link'] = '/'
            params['users_title'] = "Exit Sudo Mode"
            params['relogin_link'] = '/'
            params['DEBUG'] = app.config['DEBUG']
            return render_template("sudo.html", **params)
          else:
            error = {'code': 404, 'description': "User not found"}
            return page_not_found(error)
        else:
          logging.error("Sudo %s to %s failure", user.email(), su_email)
          error = {'code': 403, 'description': "Insufficient permission"}
          return page_not_found(error)
    return redirect(url_for('login'))

@app.route("/login")
def login():
    user = users.get_current_user()
    params = {}
    if user is None:
      return redirect(users.create_login_url('/'))
    else:
      return redirect(url_for('home'))


@app.route("/old")
def dashboard():
    user = users.get_current_user()
    params = {}
    if user is None:
        params['users_link'] = force_account_chooser(
            users.create_login_url('/#/loginLanding'))
        params['users_title'] = "Sign In"
    else:
        logging.info("User is %s", user.email())
        params["user"] = {'email': user.email()}
        params['users_link'] = users.create_logout_url('/')
        params['users_title'] = "Log Out"
        params['relogin_link'] = users.create_logout_url(
            force_account_chooser(users.create_login_url('/#/loginLanding')))
    params['DEBUG'] = app.config['DEBUG']
    return render_template("base.html", **params)

@app.route("/manage")
def admin():
    user = users.get_current_user()
    params = {}
    if user is None:
        params['users_link'] = force_account_chooser(
            users.create_login_url('/#/loginLanding'))
        params['users_title'] = "Sign In"
        return redirect(users.create_login_url('/manage'))
    else:
        logging.info("Staff Login Attempt from %s", user.email())
        userobj = models.User.lookup(user.email())

        # TODO: Filter by class.
        query = models.Participant.query(
          models.Participant.role == 'staff')
        all_staff = [part.user.id() for part in list(query.fetch())]

        if userobj.is_admin or userobj.key.id() in all_staff:
            logging.info("Staff Login Success from %s", user.email())
            params["user"] = {'id': user.user_id(), 'keyId': userobj.key.id(), 'email' : user.email()}
            params["admin"] = {'email': user.email()}
            params['users_link'] = users.create_logout_url('/')
            params['users_title'] = "Log Out"
            params['relogin_link'] = users.create_logout_url(
                force_account_chooser(
                    users.create_login_url('/#/loginLanding')))
            return render_template("admin.html", **params)
        else:
            logging.info("Staff Login Failure from %s", user.email())
            error = {'code': 403, 'description': "Insufficient permission"}
            return page_not_found(error)

## Error handlers
# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error=e), 404

# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error=e), 500

@api.parser.error_handler
def args_error(e):
    raise BadValueError(e.message)

def check_version(client):
    latest = models.Version.query(models.Version.name == 'ok').get()

    if latest is None or latest.current_version is None:
        raise APIException('Current version of ok not found')

    if client != latest.current_version:
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

            if (isinstance(rval, Response) or
                    isinstance(rval, werkzeug.wrappers.Response)):
                pass
            elif isinstance(rval, list):
                rval = utils.create_api_response(200, message, rval)
            elif (isinstance(rval, collections.Iterable)
                  and not isinstance(rval, dict)):
                rval = utils.create_api_response(*rval)
            else:
                rval = utils.create_api_response(200, message, rval)
            return rval

        except IncorrectVersionError as e:
            logging.warn(e.message)
            return utils.create_api_response(e.code, e.message, e.data)

        except APIException as e:
            logging.exception(e.message)
            return utils.create_api_response(e.code, e.message, e.data)

        except Exception as e: #pylint: disable=broad-except
            logging.exception(e.message)
            return utils.create_api_response(500, 'internal server error :(')

    app.add_url_rule(
        '%s' % url, view_func=api_wrapper, defaults={'path': None},
        methods=['GET', 'POST'])
    app.add_url_rule(
        '%s/<path:path>' % url, view_func=api_wrapper,
        methods=['GET', 'POST', 'DELETE', 'PUT'])

register_api(api.AssignmentAPI, 'assignment_api', 'assignment')
register_api(api.SubmissionAPI, 'submission_api', 'submission')
register_api(api.VersionAPI, 'version_api', 'version')
register_api(api.CourseAPI, 'course_api', 'course')
register_api(api.GroupAPI, 'group_api', 'group')
register_api(api.UserAPI, 'user_api', 'user')
register_api(api.QueueAPI, 'queue_api', 'queue')
register_api(api.FinalSubmissionAPI, 'final_submission_api', 'final_submission')
register_api(api.AnalyticsAPI, 'analytics_api', 'analytics')
