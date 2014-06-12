"""
The public API for ok.py
"""
from flask.views import MethodView
from flask.app import request
from flask import json

from app import app
from app import models
from app.models import db

API_PREFIX = '/api/v1'

class APIResource(object):
    """
    The base class for an API Resource
    """

    @classmethod
    def get_model(cls):
        """
        Get the model this api resource is associated with.
        Needs to be overridden by a subclass
        """
        return NotImplemented()

    def get(self, db_id):
        """
        The GET HTTP method
        """
        if db_id is None:
            return self.index()
        db_obj = self.get_model().query.get(db_id)
        if not db_obj:
            #TODO(stephen) Make error json, and more descriptive
            return ("Resource {} not found".format(db_id), 404, {})
        return json.dumps(db_obj)

    def put(self):
        """
        The PUT HTTP method
        """
        new_mdl = self.get_model()()
        db.session.add(new_mdl)
        db.session.commit()
        return json.dumps({'status': 200})

    def post(self):
        """
        The POST HTTP method
        """
        POST = request.json
        new_mdl = self.get_model().from_dict(POST)
        # TODO(stephen) look at what's left over in request.POST
        db.session.add(new_mdl)
        db.session.commit()
        return json.dumps({'status': 200, 'id': new_mdl.db_id})

    def delete(self, user_id):
        """
        The DELETE HTTP method
        """
        ent = self.get_model().query.get(user_id)
        db.session.delete(ent)
        db.session.commit()
        return json.dumps({'status': 200})

    def index(self):
        """
        Index HTTP method thing.
        """
        return json.dumps(self.get_model().query.all())

class UserAPI(MethodView, APIResource):
    """
    The API resource for the User Object
    """
    @classmethod
    def get_model(cls):
        return models.User

class AssignmentAPI(MethodView, APIResource):
    """
    The API resource for the Assignment Object
    """
    @classmethod
    def get_model(cls):
        return models.Assignment

class SubmissionAPI(MethodView, APIResource):
    """
    The API resource for the Submission Object
    """
    @classmethod
    def get_model(cls):
        return models.Submission

def register_api(view, endpoint, url, primary_key='db_id', pk_type='int'):
    """
    Register the given view at the endpoint, accessible by the given url.
    """
    url = API_PREFIX + url
    view_func = view.as_view(endpoint)
    app.add_url_rule(url, defaults={primary_key: None},
                     view_func=view_func, methods=['GET',])
    app.add_url_rule('%s/new' % url, view_func=view_func, methods=['POST',])
    app.add_url_rule('%s/<%s:%s>' % (url, pk_type, primary_key),
                     view_func=view_func, methods=['GET', 'PUT', 'DELETE'])

register_api(UserAPI, 'user_api', '/users')
register_api(AssignmentAPI, 'assignment_api', '/assignments')
