"""
The public API
"""
import logging

from flask.views import View
from flask.app import request, json
from flask import session, make_response
from webargs import Arg
from webargs.flaskparser import FlaskParser

from app import models
from app.codereview import compare
from app.models import BadValueError
from app.constants import API_PREFIX
from app.needs import Need
from app.utils import create_api_response, paginate, filter_query, create_zip

from google.appengine.ext import ndb

parser = FlaskParser()

def KeyArg(klass, **kwds):
    return Arg(ndb.Key, use=lambda c: {'pairs':[(klass, int(c))]}, **kwds)

def KeyRepeatedArg(klass, **kwds):
    def parse_list(key_list):
        staff_lst = key_list
        if not isinstance(key_list, list):
            if ',' in key_list:
                staff_lst = key_list.split(',')
            else:
                staff_lst = [key_list]
        return [ndb.Key(klass, x) for x in staff_lst]
    return Arg(None, use=parse_list, **kwds)

class APIResource(View):
    """The base class for API resources.

    Set the model for each subclass.
    """

    model = None
    web_args = {}
    key_type = int

    @property
    def name(self):
        return self.model.__name__

    def dispatch_request(self, path, *args, **kwargs):
        meth = request.method.upper()

        if not path: # Index
            if meth == "GET":
                return self.index()
            elif meth == "POST":
                return self.post()
            assert meth in ("GET", "POST"), 'Unimplemented method %s' % meth

        if '/' not in path:
            # For now, just allow ID gets
            assert meth in ['GET', 'PUT', 'DELETE']
            meth = getattr(self, meth.lower(), None)

            assert meth is not None, 'Unimplemented method %r' % request.method
            try:
                key = self.key_type(path)
            except (ValueError, AssertionError):
                return create_api_response(400,
                    "Invalid key. Needs to be of type '%s'" % self.key_type)
            return meth(key, *args, **kwargs)

        entity_id, action = path.split('/')
        try:
            key = self.key_type(entity_id)
        except (ValueError, AssertionError):
            return create_api_response(400,
                "Invalid key. Needs to be of type '%s'" % self.key_type)

        meth = getattr(self, action, None)
        assert meth is not None, 'Unimplemented action %r' % action
        return meth(key, *args, **kwargs)

    def get(self, key):
        """
        The GET HTTP method
        """
        obj = self.model.get_by_id(key)
        if not obj:
            return create_api_response(404, "{resource} {key} not found".format(
                resource=self.name, key=key))

        need = Need('get')
        if not obj.can(session['user'], need, obj):
            return need.api_response()

        return create_api_response(200, "", obj)

    def put(self, key):
        """
        The PUT HTTP method
        """
        obj = self.model.get_by_id(key)
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
                return create_api_response(
                    400, "{} is not a valid field.".format(key))

            setattr(obj, key, value)
            changed = True

        if changed:
            obj.put()

        return create_api_response(200, "", obj)

    def post(self):
        """
        The POST HTTP method
        """
        data = self.parse_args(False)

        entity, error_response = self.new_entity(data)
        if error_response:
            return error_response

        need = Need('create')
        if not self.model.can(session['user'], need, obj=entity):
            return need.api_response()

        entity.put()

        return create_api_response(201, "success", {
            'key': entity.key.id()
        })

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        Returns (entity, error_response) should be ignored if error_response
        is a True value.
        """
        entity = self.model.from_dict(attributes)
        return entity, None

    def delete(self, user_id):
        """
        The DELETE HTTP method
        """
        ent = self.model.query.get(user_id)

        need = Need('delete')
        if not self.model.can_static(session['user'], need):
            return need.api_response()

        ent.key.delete()
        return create_api_response(200, "success", {})

    def parse_args(self, index):
        """
        Parses the arguments to this API call.
        |index| is whether or not this is an index call.
        """
        def use_fields(field):
            if not field[0] == '{':
                return field
            return json.loads(field)

        fields = parser.parse({
            'fields': Arg(None, use=use_fields)
        })
        request.fields = fields

        return {k:v for k, v in parser.parse(self.web_args).iteritems() if v}

    def index(self):
        """
        Index HTTP method. Should be called from GET when no key is provided.

        Processes cursor and num_page URL arguments for pagination support.
        """
        query = self.model.query()
        need = Need('index')

        result = self.model.can(session['user'], need, query=query)
        if not result:
            return need.api_response()

        args = self.parse_args(True)
        query = filter_query(result, args, self.model)
        created_prop = getattr(self.model, 'created', None)
        if not query.orders and created_prop:
            logging.info("Adding default ordering by creation time.")
            query = query.order(-created_prop)

        page = int(request.args.get('page', 1))
        num_page = request.args.get('num_page', None)
        query_results = paginate(query, page, num_page)

        add_statistics = request.args.get('stats', False)
        if add_statistics:
            query_results['statistics'] = self.statistics()
        return create_api_response(200, "success", query_results)

    def statistics(self):
        return {
            'total': self.model.query().count()
        }


class UserAPI(APIResource):
    """The API resource for the User Object"""
    model = models.User
    key_type = str

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        """
        if 'email' not in attributes:
            return None, create_api_response(400, 'Email required')
        entity = self.model.get_by_id(attributes['email'])
        if entity:
            return None, create_api_response(400,
                                             '%s already exists' % self.name)
        entity = self.model.from_dict(attributes)
        return entity, None

    web_args = {
        'first_name': Arg(str),
        'last_name': Arg(str),
        'email': Arg(str),
        'login': Arg(str),
        'course': KeyArg('User'),
    }


class AssignmentAPI(APIResource):
    """The API resource for the Assignment Object"""
    model = models.Assignment

    web_args = {
        'name': Arg(str),
        'points': Arg(float),
        'course': KeyArg('Course'),
        'templates': Arg(str, use=lambda temps: json.dumps(temps)),
    }

    def parse_args(self, is_index):
        data = super(AssignmentAPI, self).parse_args(is_index)
        if not is_index:
            data['creator'] = session['user'].key
        return data

    def group(self, key):
        obj = self.model.get_by_id(key)
        if not obj:
            return create_api_response(404, "{resource} {key} not found".format(
                resource=self.name, key=key))

        need = Need('get')
        if not obj.can(session['user'], need, obj):
            return need.api_response()

        groups = (models.Group.query()
                  .filter(models.Group.members == session['user'].key)
                  .filter(models.Group.assignment == obj.key).fetch())

        if len(groups) > 1:
            return create_api_response(409, "You are in multiple groups", groups)
        elif not groups:
            return create_api_response(200, "You are not in any groups", [])
        else:
            return create_api_response(200, "success", groups[0])


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


class SubmissionAPI(APIResource):
    """The API resource for the Submission Object"""
    model = models.Submission
    diff_model = models.SubmissionDiff

    db = SubmitNDBImplementation()

    def download(self, key):
        """
        Allows you to download a submission.
        """
        obj = self.model.get_by_id(key)
        if not obj:
            return create_api_response(404, "{resource} {key} not found".format(
                resource=self.name, key=key))

        need = Need('get')
        if not obj.can(session['user'], need, obj):
            return need.api_response()

        if 'file_contents' not in obj.messages:
            return create_api_response(400,
                "Submission has no contents to download.")

        response = make_response(create_zip(obj.messages['file_contents']))
        response.headers["Content-Disposition"] = (
            "attachment; filename=submission-%s.zip" % str(obj.created))
        response.headers["Content-Type"] = "application/zip"
        return response

    def diff(self, key):
        """
        Gets the associated diff for a submission
        """
        obj = self.model.get_by_id(key)
        if not obj:
            return create_api_response(404, "{resource} {key} not found".format(
                resource=self.name, key=key))

        need = Need('get')
        if not obj.can(session['user'], need, obj):
            return need.api_response()

        if 'file_contents' not in obj.messages:
            return create_api_response(400,
                "Submission has no contents to diff.")

        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if diff_obj:
            return create_api_response(200, "success", diff_obj.diff)

        diff = {}
        templates = obj.assignment.get().templates
        if not templates:
            return create_api_response(500,
                "No templates for assignment yet... Contact course staff")

        templates = json.loads(templates)
        for filename, contents in obj.messages['file_contents'].items():
            diff[filename] = compare.diff(templates[filename], contents)

        self.diff_model(id=obj.key.id(),
                        diff=diff).put()
        return create_api_response(200, "success", diff)

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

    def post(self):
        data = self.parse_args(False)
        if 'assignment' not in data:
            raise BadValueError("Missing required arguments 'assignment'")
        if 'messages' not in data:
            raise BadValueError("Missing required arguments 'messages'")

        return self.submit(session['user'], data['assignment'],
                           data['messages'])

    web_args = {
        'assignment': Arg(str),
        'messages': Arg(None),
    }


class VersionAPI(APIResource):
    model = models.Version

    web_args = {
        'file_data': Arg(str),
        'name': Arg(str),
        'version': Arg(str),
    }

class CourseAPI(APIResource):
    model = models.Course

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

class GroupAPI(APIResource):
    model = models.Group

    web_args = {
        'members': KeyRepeatedArg('User'),
        'name': Arg(str),
        'assignment': KeyArg('Assignment')
    }
