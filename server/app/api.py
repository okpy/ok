from sqlalchemy.ext.serializer import loads, dumps

from flask.views import MethodViewType, MethodView
from flask.app import request
from flask import json

from app import app
from app import models

API_PREFIX = '/api/v1'

def to_json(wrapped):
    def wrapper(*args, **kwds):
        rval = wrapped(*args, **kwds)
        if type(rval) is not str:
            rval = json.dumps(rval)
        return rval
    return wrapper

class APIResource():
    @to_json
    def get(self, user_id):
        if user_id is None:
            return self.index()
        return self._model.query.get(user_id)

    @to_json
    def put(self):
        new_mdl = self._model()

    @to_json
    def post(self):
        new_mdl = self._model(request.form)
        db.session.add(new_mdl)
        db.session.commit()

    @to_json
    def delete(self, user_id):
        ent = self._model.get(user_id)
        db.session.delete(ent)
        db.session.commit()

    @to_json
    def index(self):
        return self._model.query.all()

class UserAPI(MethodView, APIResource):
    _model = models.User

class AssignmentAPI(MethodView, APIResource):
    _model = models.User

    class SubmissionAPI(MethodView, APIResource):
        _model = models.User

def register_api(view, endpoint, url, pk='id', pk_type='int'):
    url = API_PREFIX + url
    view_func = view.as_view(endpoint)
    app.add_url_rule(url, defaults={pk: None},
                     view_func=view_func, methods=['GET',])
    app.add_url_rule(url, view_func=view_func, methods=['POST',])
    app.add_url_rule('%s/<%s:%s>' % (url, pk_type, pk), view_func=view_func,
                     methods=['GET', 'PUT', 'DELETE'])

register_api(UserAPI, 'user_api', '/users', pk='user_id')
