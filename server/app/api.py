"""
The public API
"""
import json
from functools import wraps

from flask.views import MethodView
from flask.app import request
from flask import session, make_response
from webargs import Arg
from webargs.flaskparser import FlaskParser

from app import models
from app import app
from app.models import BadValueError
from app.needs import Need
from app.decorators import handle_error
from app.utils import create_api_response, paginate, filter_query, create_zip

from google.appengine.ext import db, ndb

def KeyArg(klass, **kwds):
    return Arg(ndb.Key, use=lambda c:{'pairs':[(klass, int(c))]}, **kwds)

def KeyRepeatedArg(klass, **kwds):
    def parse_list(key_list):
        staff_lst = None
        if isinstance(key_list, list):
            staff_lst = key_list
        else:
            if ',' in key_list:
                staff_lst = key_list.split(',')
            else:
                staff_lst = [key_list]
        return [ndb.Key(klass, x) for x in staff_lst]
    return Arg(None, use=parse_list, **kwds)

class APIResource(object):
    """The base class for API resources.

    Set the name and get_model for each subclass.
    """

    name = None
    web_args = {}

    @classmethod
    def get_model(cls):
        """
        Get the model this API resource is associated with.
        Needs to be overridden by a subclass.
        """
        raise NotImplementedError

    @handle_error
    def get(self, key):
        """
        The GET HTTP method
        """
        if key is None:
            return self.index()

        obj = self.get_model().get_by_id(key)
        if not obj:
            return create_api_response(404, "{resource} {key} not found".format(
                resource=self.name, key=key))

        need = Need('get')
        if not obj.can(session['user'], need, obj):
            return need.api_response()

        return create_api_response(200, "", obj)

    @handle_error
    def put(self, key):
        """
        The PUT HTTP method
        """
        obj = self.get_model().get_by_id(key)
        if not obj:
            return create_api_response(404, "{resource} {key} not found".format(
                resource=self.name, key=key))

        need = Need('get')
        if not obj.can(session['user'], need, obj):
            return need.api_response()

        need = Need('put')
        if not obj.can(session['user'], need, obj):
            return need.api_response()

        blank_val = object()
        changed = False
        for key, value in self.parse_args(False).iteritems():
            old_val = getattr(obj, key, blank_val)
            if old_val == blank_val:
                return create_api_response(400, "{} is not a valid field.".format(key))

            setattr(obj, key, value)
            changed = True

        if changed:
            obj.put()

        return create_api_response(200, "", obj)

    @handle_error
    def post(self):
        """
        The POST HTTP method
        """
        data = self.parse_args(False)

        need = Need('create')
        if not self.get_model().can(session['user'], need):
            return need.api_response()

        entity, error_response = self.new_entity(data)

        if not error_response:
            return create_api_response(200, "success", {
                'key': entity.key.id()
            })
        else:
            return error_response

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        Returns (entity, error_response) should be ignored if error_response
        is a True value.
        """
        entity = self.get_model().from_dict(attributes)
        entity.put()
        return entity, None

    @handle_error
    def delete(self, user_id):
        """
        The DELETE HTTP method
        """
        ent = self.get_model().query.get(user_id)

        need = Need('delete')
        if not self.get_model().can_static(session['user'], need):
            return need.api_response()

        ent.key.delete()
        return create_api_response(200, "success", {})

    def parse_args(self, index):
        """
        Parses the arguments to this API call.
        |index| is whether or not this is an index call.
        """
        return {k:v for k,v in parser.parse(self.web_args).iteritems() if v}

    def index(self):
        """
        Index HTTP method. Should be called from GET when no key is provided.

        Processes cursor and num_page URL arguments for pagination support.
        """
        query = self.get_model().query()
        need = Need('index')

        result = self.get_model().can(session['user'], need, query=query)
        if not result:
            return need.api_response()

        args = self.parse_args(True)
        query = filter_query(result, args, self.get_model())
        created_prop = getattr(self.get_model(), 'created', None)
        if not query.orders and created_prop:
            query = query.order(-created_prop)

        cursor = request.args.get('cursor', None)
        num_page = request.args.get('num_page', None)
        query_results = paginate(query, cursor, num_page)
        return create_api_response(200, "success", query_results)


parser = FlaskParser()


class UserAPI(MethodView, APIResource):
    """The API resource for the User Object"""
    name = "User"

    @classmethod
    def get_model(cls):
        return models.User

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        """
        if 'email' not in attributes:
            return None, create_api_response(400, 'Email required')
        entity = self.get_model().get_by_id(attributes['email'])
        if entity:
            return None, create_api_response(400,
                                             '%s already exists' % self.name)
        entity = self.get_model().from_dict(attributes)
        entity.put()
        return entity, None

    web_args = {
        'first_name': Arg(str),
        'last_name': Arg(str),
        'email': Arg(str),
        'login': Arg(str),
        'course': KeyArg('User'),
    }


class AssignmentAPI(MethodView, APIResource):
    """The API resource for the Assignment Object"""
    name = "Assignment"

    @classmethod
    def get_model(cls):
        return models.Assignment

    web_args = {
        'name': Arg(str),
        'points': Arg(float),
        'course': KeyArg('Course'),
    }

    def parse_args(self, is_index):
        data = super(AssignmentAPI, self).parse_args(is_index)
        if not is_index:
            data['creator'] = session['user'].key
        return data


class SubmitNDBImplementation(object):
    """Implementation of DB calls required by submission using Google NDB"""

    def lookup_assignments_by_name(self, name):
        """Look up all assignments of a given name."""
        by_name = models.Assignment.name == name
        return list(models.Assignment.query().filter(by_name))

    def create_submission(self, user, assignment, messages):
        """Create submission using user as parent to ensure ordering."""
        submission = models.Submission(submitter=user.key,
                                       assignment=assignment.key,
                                       messages=messages)
        submission.put()
        return submission


class SubmissionAPI(MethodView, APIResource):
    """The API resource for the Submission Object"""
    name = "Submission"
    db = SubmitNDBImplementation()
    post_fields = ['assignment', 'messages']

    @handle_error
    def get(self, key):
        """
        The GET HTTP method
        """
        if key is None:
            return self.index()

        obj = self.get_model().get_by_id(key)
        if not obj:
            return create_api_response(404, "{resource} {key} not found".format(
                resource=self.name, key=key))

        need = Need('get')
        if not obj.can(session['user'], need, obj):
            return need.api_response()

        if request.args.get('download') == 'true' \
                and 'file_contents' in obj.messages:
            response = make_response(create_zip(obj.messages['file_contents']))
            response.headers["Content-Disposition"] = "attachment; filename=submission-%s.zip" % str(obj.created)
            response.headers["Content-Type"] = "application/zip"
            return response
        return create_api_response(200, "", obj)

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
    def post(self):
        data = self.parse_args(False)

        try:
            return self.submit(session['user'], data['assignment'],
                               data['messages'])
        except BadValueError as e:
            return create_api_response(400, e.message, {})

    web_args = {
        'assignment': Arg(str),
        'messages': Arg(None),
    }


class VersionAPI(APIResource, MethodView):
    name = "Version"

    @classmethod
    def get_model(cls):
        return models.Version

    web_args = {
        'file_data': Arg(str),
        'name': Arg(str),
        'version': Arg(str),
    }

class CourseAPI(APIResource, MethodView):
    name = "Course"

    @classmethod
    def get_model(cls):
        return models.Course

    def parse_args(self, is_index):
        data = super(CourseAPI, self).parse_args(is_index)
        if not is_index:
            data['creator'] = session['user'].key
        return data

    web_args = {
        'staff': KeyRepeatedArg('User'),
        'name': Arg(str),
        'offering': Arg(str),
        'institution': Arg(str),
    }
