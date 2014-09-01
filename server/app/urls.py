"""
URL dispatch route mappings and error handlers
"""
from functools import wraps

from flask import render_template, session

from app import app
from app import api
from app import auth
from app.constants import API_PREFIX

@app.route("/")
def index():
    return "Hello world"

## Error handlers
# Handle 404 errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', error=e), 404

# Handle 500 errors
@app.errorhandler(500)
def server_error(e):
    return render_template('500.html', error=e), 500

def register_api(view, endpoint, url, primary_key='key', pk_type='int:'):
    """
    Registers the given view at the endpoint, accessible by the given url.
    """
    url = API_PREFIX + url
    view = view.as_view(endpoint)

    @wraps(view)
    def wrapped(*args, **kwds):
        session['user'] = auth.authenticate()
        return view(*args, **kwds)

    # To get all objects
    app.add_url_rule(url, defaults={primary_key: None},
                     view_func=wrapped, methods=['GET', ])

    # To create a new object
    app.add_url_rule('%s/new' % url, view_func=wrapped, methods=['POST', ])

    # To operate on individual object
    app.add_url_rule('%s/<%s%s>' % (url, pk_type, primary_key),
                     view_func=wrapped, methods=['GET', 'PUT', 'DELETE'])

register_api(api.UserAPI, 'user_api', '/user', pk_type='')
register_api(api.AssignmentAPI, 'assignment_api', '/assignment')
register_api(api.SubmissionAPI, 'submission_api', '/submission')

