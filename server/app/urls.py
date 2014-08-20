"""
URL dispatch route mappings and error handlers
"""
from functools import wraps
import collections

from flask import render_template, session

from app import app
from app import api
from app import auth
from app.constants import API_PREFIX
from app.needs import Need
from app.utils import create_api_response

@app.route("/")
def index():
    return "Hello world"

## Error handlers
# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

def register_api(view, endpoint, url, primary_key='key', pk_type='int:', admin=False):
    """
    Registers the given view at the endpoint, accessible by the given url.
    """
    url = API_PREFIX + url
    view = view.as_view(endpoint)

    @wraps(view)
    def wrapped(*args, **kwds):
        session['user'] = auth.authenticate()
        return view(*args, **kwds)

    app.add_url_rule(url, defaults={primary_key: None},
                     view_func=wrapped, methods=['GET', ])
    app.add_url_rule('%s/new' % url, view_func=wrapped, methods=['POST', ])
    app.add_url_rule('%s/<%s%s>' % (url, pk_type, primary_key),
                     view_func=wrapped, methods=['GET', 'PUT', 'DELETE'])

# TODO(denero) Add appropriate authentication requirements
register_api(api.UserAPI, 'user_api', '/user', admin=True, pk_type='')
register_api(api.AssignmentAPI, 'assignment_api', '/assignment', admin=True)
register_api(api.SubmissionAPI, 'submission_api', '/submission')

