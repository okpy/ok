"""
The public API
"""
import datetime
import logging
import datetime

from flask.views import View
from flask.app import request, json
from flask import session, make_response
from webargs import Arg
from webargs.flaskparser import FlaskParser

from app import models, app
from app.codereview import compare
from app.constants import API_PREFIX
from app.needs import Need
from app.utils import paginate, filter_query, create_zip

from app.exceptions import *

from google.appengine.ext import ndb

parser = FlaskParser()

def DateTimeArg(**kwds):
    def parse_date(arg):
        op = None
        if '|' in arg:
            op, arg = arg.split('|', 1)

        date = datetime.datetime.strptime(arg, app.config["GAE_DATETIME_FORMAT"])
        delta = datetime.timedelta(hours = 7)
        date = (datetime.datetime.combine(date.date(),date.time()) + delta)
        return (op, date) if op else date
    return Arg(None, use=parse_date)

def KeyArg(klass, **kwds):
    def parse_key(key):
        try:
            key = int(key)
        except (ValueError, TypeError):
            pass
        return {'pairs': [(klass, key)]}
    return Arg(ndb.Key, use=parse_key, **kwds)

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
    methods = {}
    key_type = int

    @property
    def name(self):
        return self.model.__name__

    def get_instance(self, key, user):
        obj = self.model.get_by_id(key)
        if not obj:
            raise ResourceDoesntExistError("{resource} {key} not found".format(
                resource=self.name, key=key))

        need = Need('get')
        if not obj.can(user, need, obj):
            raise PermissionError(need)
        return obj

    def call_method(self, method_name, user, instance=None, is_index=False,
                    http_method=None):
        if method_name not in self.methods:
            raise BadMethodError('Unimplemented method %s' % method_name)
        constraints = self.methods[method_name]
        if "methods" in constraints:
            if http_method is None:
                raise IncorrectHTTPMethodError('Need to specify HTTP method')
            if http_method not in constraints["methods"]:
                raise IncorrectHTTPMethodError('Bad HTTP Method: %s' % http_method)
        data = {}
        web_args = constraints.get('web_args', {})
        data = self.parse_args(web_args, user, is_index=is_index)
        method = getattr(self, method_name)
        if instance is not None:
            return method(instance, user, data)
        return method(user, data)

    def dispatch_request(self, path, *args, **kwargs):
        request.fields = {}
        http_method = request.method.upper()
        user = session['user']

        if path is None: # Index
            if http_method not in ("GET", "POST"):
                raise IncorrectHTTPMethodError('Incorrect HTTP method: %s' % http_method)
            method_name = "index" if http_method == "GET" else http_method.lower()
            return self.call_method(method_name, user, is_index=(method_name == "index"))

        path = path.split('/')
        if len(path) == 1:
            entity_id = path[0]
            try:
                key = self.key_type(entity_id)
            except (ValueError, AssertionError):
                raise BadValueError("Invalid key. Needs to be of type: %s" % self.key_type)
            instance = self.get_instance(key, user)
            method_name = http_method.lower()
            return self.call_method(method_name, user, instance=instance)

        entity_id, method_name = path
        try:
            key = self.key_type(entity_id)
        except (ValueError, AssertionError):
            raise BadValueError("Invalid key. Needs to be of type: %s" % self.key_type)
        instance = self.get_instance(key, user)
        return self.call_method(method_name, user, instance=instance, http_method=http_method)


    def get(self, obj, user, data):
        """
        The GET HTTP method
        """
        return obj

    def put(self, obj, user, data):
        """
        The PUT HTTP method
        """
        need = Need('put')
        if not obj.can(user, need, obj):
            raise PermissionError(need)

        blank_val = object()
        changed = False
        for key, value in self.parse_args(False, user).iteritems():
            old_val = getattr(obj, key, blank_val)
            if old_val == blank_val:
                return 400, "{} is not a valid field.".format(key)

            setattr(obj, key, value)
            changed = True

        if changed:
            obj.put()

        return obj

    def post(self, user, data):
        """
        The POST HTTP method
        """
        data = self.parse_args(False, user)

        entity, error_response = self.new_entity(data)
        if error_response:
            return error_response

        need = Need('create')
        if not self.model.can(user, need, obj=entity):
            raise PermissionError(need)

        entity.put()

        return {
            'key': entity.key.id()
        }

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        Returns (entity, error_response) should be ignored if error_response
        is a True value.
        """
        entity = self.model.from_dict(attributes)
        return entity, None

    def delete(self, obj, user, data):
        """
        The DELETE HTTP method
        """
        need = Need('delete')
        if not self.model.can(user, need, obj=obj):
            return need.api_response()

        obj.key.delete()
        return None

    def parse_args(self, web_args, user, is_index=False):
        """
        Parses the arguments to this API call.
        |index| is whether or not this is an index call.
        """
        def use_fields(field):
            if not field[0] == '{':
                if field == "false":
                    return False
                elif field == "true":
                    return True
                return field
            return json.loads(field)

        fields = parser.parse({
            'fields': Arg(None, use=use_fields)
        })
        if fields['fields'] is None:
            fields['fields'] = {}
        if type(fields['fields']) != dict and type(fields['fields']) != bool:
            raise BadValueError("fields should be dictionary or boolean")
        request.fields = fields
        return {k:v for k, v in parser.parse(web_args).iteritems() if v != None}


    def index(self, user, data):
        """
        Index HTTP method. Should be called from GET when no key is provided.

        Processes cursor and num_page URL arguments for pagination support.
        """
        query = self.model.query()
        need = Need('index')

        result = self.model.can(user, need, query=query)
        if not result:
            raise PermissionError(need)

        query = filter_query(result, data, self.model)
        created_prop = getattr(self.model, 'created', None)
        if not query.orders and created_prop:
            logging.info("Adding default ordering by creation time.")
            query = query.order(-created_prop, self.model.key)

        page = int(request.args.get('page', 1))
        num_page = request.args.get('num_page', None)
        query_results = paginate(query, page, num_page)

        add_statistics = request.args.get('stats', False)
        if add_statistics:
            query_results['statistics'] = self.statistics()
        return query_results

    def statistics(self):
        return {
            'total': self.model.query().count()
        }


class UserAPI(APIResource):
    """The API resource for the User Object"""
    model = models.User
    key_type = str

    methods = {
        'post': {
            'web_args': {
                'first_name': Arg(str),
                'last_name': Arg(str),
                'email': Arg(str, required=True),
                'login': Arg(str),
            }
        },
        'get': {
        },
        'index': {
        },
        'invitations': {
            'methods': set(['GET']),
            'web_args': {
                'first_name': Arg(str),
                'last_name': Arg(str),
                'email': Arg(str, required=True),
                'login': Arg(str),
            }
        },
        'accept_invitation': {
            'methods': set(['POST']),
            'web_args': {
            }
        },
        'reject_invitation': {
            'methods': set(['POST']),
            'web_args': {
            }
        },
    }

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        """
        entity = self.model.get_by_id(attributes['email'])
        if entity:
            return None, (400, '%s already exists' % self.name)
        entity = self.model.from_dict(attributes)
        return entity, None


    def invitations(self, user, obj):
        pass

    def accept_invitation(self, user, obj):
        pass

    def reject_invitation(self, user, obj):
        pass



class AssignmentAPI(APIResource):
    """The API resource for the Assignment Object"""
    model = models.Assignment

    methods = {
        'post': {
            'web_args': {
                'name': Arg(str, required=True),
                'display_name': Arg(str, required=True),
                'points': Arg(float, required=True),
                'course': KeyArg('Course', required=True),
                'max_group_size': Arg(int, required=True),
                'templates': Arg(str, use=lambda temps: json.dumps(temps), required=True),
            }
        },
        'get': {
        },
        'index': {
        },
        'group': {
            'methods': set(['GET'])
        },
    }

    def post(self, user, data):
        """
        The POST HTTP method
        """
        data['creator'] = user.key
        return super(AssignmentAPI, self).post(user, data)


    def group(self, obj, user, data):
        groups = (models.Group.query()
                  .filter(models.Group.members == user.key)
                  .filter(models.Group.assignment == obj.key).fetch())

        if len(groups) > 1:
            return (409, "You are in multiple groups", {
                "groups": groups
            })
        elif not groups:
            return (200, "You are not in any groups", {
                "in_group": False,
            })
        else:
            return groups[0]


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

    methods = {
        'post': {
            'web_args': {
                'assignment': Arg(str, required=True),
                'messages': Arg(None, required=True),
            }
        },
        'get': {
            'web_args': {
            }
        },
        'index': {
            'web_args': {
            }
        },
        'diff': {
            'methods': set(["GET"]),
        },
        'download': {
            'methods': set(["GET"]),
        },
    }

    def download(self, obj, user, data):
        """
        Allows you to download a submission.
        """
        if 'file_contents' not in obj.messages:
            raise BadValueError("Submission has no contents to download")

        response = make_response(create_zip(obj.messages['file_contents']))
        response.headers["Content-Disposition"] = (
            "attachment; filename=submission-%s.zip" % str(obj.created))
        response.headers["Content-Type"] = "application/zip"
        return response

    def diff(self, obj, user, data):
        """
        Gets the associated diff for a submission
        """
        if 'file_contents' not in obj.messages:
            return 400, "Submission has no contents to diff."

        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if diff_obj:
            return diff_obj

        diff = {}
        templates = obj.assignment.get().templates
        if not templates:
            return (500,
                "No templates for assignment yet... Contact course staff")

        templates = json.loads(templates)
        for filename, contents in obj.messages['file_contents'].items():
            diff[filename] = compare.diff(templates[filename], contents)

        diff = self.diff_model(id=obj.key.id(),
                               diff=diff)
        diff.put()
        return diff

    def add_comment(self, obj, user, data):
        """
        Adds a comment to this diff.
        """
        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if not diff_obj:
            raise BadValueError("Diff doesn't exist yet")

        index = data["index"]
        message = data["message"]
        filename = data["file"]

        if message.strip() == "":
            raise BadValueError("Cannot make empty comment")

        comment = models.Comment(
            filename=filename,
            message=message,
            line=index,
            author=user.key,
            parent=diff_obj.key)
        comment.put()

    def delete_comment(self, obj, user, data):
        """
        Deletes a comment on this diff.
        """
        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if not diff_obj:
            raise BadValueError("Diff doesn't exist yet")

        comment = data.get('comment', None)
        if not comment:
            return 400, "Missing required argument 'comment'"

        comment = models.Comment.get_by_id(comment, parent=diff_obj.key)
        if comment:
            comment.key.delete()

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
        return {
            'key': submission.key.id()
        }

    def post(self, user, data):
        return self.submit(user, data['assignment'],
                           data['messages'])


class VersionAPI(APIResource):
    model = models.Version

    methods = {
        'post': {
            'web_args': {
                'file_data': Arg(str, required=True),
                'name': Arg(str, required=True),
                'version': Arg(str, required=True),
            }
        },
        'get': {
        },
        'index': {
        },
    }

class CourseAPI(APIResource):
    model = models.Course

    methods = {
        'post': {
            'web_args': {
                'staff': KeyRepeatedArg('User', required=True),
                'name': Arg(str, required=True),
                'offering': Arg(str, required=True),
                'institution': Arg(str, required=True),
            }
        },
        'get': {
        },
        'index': {
        },
    }

    def post(self, user, data):
        """
        The POST HTTP method
        """
        data['creator'] = user.key
        return super(AssignmentAPI, self).post(user, data)



class GroupAPI(APIResource):
    model = models.Group

    methods = {
        'post': {
            'web_args': {
                'assignment': KeyArg('Assignment', required=True)
            }
        },
        'get': {
        },
        'index': {
        },
        'add_member': {
            'methods': set(['POST']),
            'web_args': {
                'member': KeyArg('User', required=True),
            },
        },
        'remove_member': {
            'methods': set(['POST']),
            'web_args': {
                'member': KeyArg('User', required=True),
            },
        }
    }

    def add_member(self, obj, user, data):
        pass

    def remove_member(self, obj, user, data):
        pass
