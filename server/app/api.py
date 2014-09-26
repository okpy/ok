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

        date = datetime.datetime.strptime(arg,
                                          app.config["GAE_DATETIME_FORMAT"])
        delta = datetime.timedelta(hours=7)
        date = (datetime.datetime.combine(date.date(), date.time()) + delta)
        return (op, date) if op else date
    return Arg(None, use=parse_date, **kwds)


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
            raise BadKeyError(key)

        need = Need('get')
        if not obj.can(user, need, obj):
            raise need.exception()
        return obj

    def call_method(self, method_name, user, http_method,
                    instance=None, is_index=False):
        if method_name not in self.methods:
            raise BadMethodError('Unimplemented method %s' % method_name)
        constraints = self.methods[method_name]
        if "methods" in constraints:
            if http_method is None:
                raise IncorrectHTTPMethodError('Need to specify HTTP method')
            if http_method not in constraints["methods"]:
                raise IncorrectHTTPMethodError('Bad HTTP Method: %s'
                                               % http_method)
        data = {}
        web_args = constraints.get('web_args', {})
        data = self.parse_args(web_args, user, is_index=is_index)
        method = getattr(self, method_name)
        if instance is not None:
            return method(instance, user, data)
        return method(user, data)

    def dispatch_request(self, path, *args, **kwargs):
        http_method = request.method.upper()
        user = session['user']

        if path is None:  # Index
            if http_method not in ("GET", "POST"):
                raise IncorrectHTTPMethodError('Incorrect HTTP method: %s'
                                               % http_method)
            method_name = ("index" if http_method == "GET"
                           else http_method.lower())
            return self.call_method(method_name, user, http_method,
                                    is_index=(method_name == "index"))

        path = path.split('/')
        if len(path) == 1:
            entity_id = path[0]
            try:
                key = self.key_type(entity_id)
            except (ValueError, AssertionError):
                raise BadValueError("Invalid key. Needs to be of type: %s"
                                    % self.key_type)
            instance = self.get_instance(key, user)
            method_name = http_method.lower()
            return self.call_method(method_name, user, http_method,
                                    instance=instance)

        entity_id, method_name = path
        try:
            key = self.key_type(entity_id)
        except (ValueError, AssertionError):
            raise BadValueError("Invalid key. Needs to be of type: %s"
                                % self.key_type)
        instance = self.get_instance(key, user)
        return self.call_method(method_name, user, http_method,
                                instance=instance)

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
            raise need.exception()

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
        entity = self.new_entity(data)

        need = Need('create')
        if not self.model.can(user, need, obj=entity):
            raise need.exception()

        entity.put()

        return (201, {
            'key': entity.key.id()
        })

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        Returns (entity, error_response) should be ignored if error_response
        is a True value.
        """
        return self.model.from_dict(attributes)

    def delete(self, obj, user, data):
        """
        The DELETE HTTP method
        """
        need = Need('delete')
        if not self.model.can(user, need, obj=obj):
            raise need.exception()

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
        return {k: v for k, v in parser.parse(web_args).iteritems()
                if v is not None}

    def index(self, user, data):
        """
        Index HTTP method. Should be called from GET when no key is provided.

        Processes cursor and num_page URL arguments for pagination support.
        """
        query = self.model.query()
        need = Need('index')

        result = self.model.can(user, need, query=query)
        if not result:
            raise need.exception()

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
                'assignment': KeyArg('Assignment')
            }
        },
    }

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        """
        entity = self.model.get_by_id(attributes['email'])
        if entity:
            raise BadValueError("user already exists")
        entity = self.model.from_dict(attributes)
        return entity

    def invitations(self, user, obj, data):
        query = models.Group.query(models.Group.invited_members == user.key)
        if 'assignment' in data:
            query = query.filter(models.Group.assignment == data['assignment'])
        return list(query)


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
                'due_date': DateTimeArg(required=True),
                'templates': Arg(str, use=lambda temps: json.dumps(temps),
                                 required=True),
            }
        },
        'get': {
        },
        'index': {
            'web_args': {
                'course': KeyArg('Course'),
            }
        },
    }

    def post(self, user, data):
        """
        The POST HTTP method
        """
        data['creator'] = user.key
        return super(AssignmentAPI, self).post(user, data)


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
                # fill in filter parameters
            }
        },
        'diff': {
            'methods': set(["GET"]),
        },
        'download': {
            'methods': set(["GET"]),
        },
        'add_comment': {
            'methods': set(["POST"]),
            'web_args': {
                'index': Arg(int, required=True),
                'file': Arg(str, required=True),
                'message': Arg(str, required=True)
            }
        },
        'delete_comment': {
            'methods': set(["POST"]),
            'web_args': {
                'comment': KeyArg('Comment', required=True)
            }
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
            raise BadValueError("Submission has no contents to diff")

        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if diff_obj:
            return diff_obj

        diff = {}
        templates = obj.assignment.get().templates
        if not templates:
            raise BadValueError("no templates for assignment, \
                                please contact course staff")

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
            raise ResourceDoesntExistError("comment doesn't exist")

        comment = models.Comment.get_by_id(comment.id(), parent=diff_obj.key)
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
        submission = self.db.create_submission(user, valid_assignment,
                                               messages)
        return (201, "success", {
            'key': submission.key.id()
        })

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
                'name': Arg(str, required=True),
                'offering': Arg(str, required=True),
                'institution': Arg(str, required=True),
                'active': Arg(bool),
            }
        },
        'delete': {
        },
        'get': {
        },
        'index': {
        },
        'add_staff': {
            'methods': set(['POST']),
            'web_args': {
                'staff_member': KeyArg('User', required=True)
            }
        },
        'remove_staff': {
            'methods': set(['POST']),
            'web_args': {
                'staff_member': KeyArg('User', required=True)
            }
        },
        'assignments': {
            'methods': set(['GET']),
            'web_args': {
            }
        },
    }

    def post(self, user, data):
        """
        The POST HTTP method
        """
        data['creator'] = user.key
        return super(CourseAPI, self).post(user, data)

    def add_staff(self, course, user, data):
        need = Need("staff")
        if not course.can(user, need, course):
            raise need.exception()

        if data['staff_member'] not in course.staff:
            user = models.User.get_or_insert(data['staff_member'].id())
            course.staff.append(user.key)
            course.put()

    def remove_staff(self, course, user, data):
        need = Need("staff")
        if not course.can(user, need, course):
            raise need.exception()
        if data['staff_member'] in course.staff:
            course.staff.remove(data['staff_member'])
            course.put()

    def assignments(self, course, user, data):
        return list(course.assignments)

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
            'web_args': {
                'assignment': KeyArg('Assignment')
            }
        },
        'add_member': {
            'methods': set(['PUT']),
            'web_args': {
                'member': KeyArg('User', required=True),
            },
        },
        'remove_member': {
            'methods': set(['PUT']),
            'web_args': {
                'member': KeyArg('User', required=True),
            },
        },
        'accept_invitation': {
            'methods': set(['PUT']),
        },
        'reject_invitation': {
            'methods': set(['PUT']),
        }
    }

    def post(self, user, data):
        # no permissions necessary, anyone can create a group
        current_group = list(user.groups(data['assignment']))
        if len(current_group) == 1:
            raise BadValueError("already in a group")
        if len(current_group) > 1:
            raise BadValueError("in multiple groups")
        group = self.new_entity(data)
        group.members.append(user.key)
        group.put()


    def add_member(self, group, user, data):
        # can only remove a member if you are a member
        need = Need('member')
        if not group.can(user, need, group):
            raise need.exception()
        if data['member'] in group.invited_members:
            raise BadValueError("user has already been invited")
        if data['member'] in group.members:
            raise BadValueError("user already part of group")
        user = models.User.get_or_insert(data['member'].id())
        group.invited_members.append(user.key)
        group.put()

    def remove_member(self, group, user, data):
        # can only remove a member if you are a member
        need = Need('member')
        if not group.can(user, need, group):
            raise need.exception()
        if data['member'] in group.members:
            group.members.remove(data['member'])
        elif data['member'] in group.invited_members:
            group.invited_members.remove(data['member'])
        if len(group.members) == 0:
            group.key.delete()
        else:
            group.put()

    def accept_invitation(self, group, user, data):
        # can only accept an invitation if you are in the invited_members
        need = Need('invitation')
        if not group.can(user, need, group):
            raise need.exception()
        assignment = group.assignment.get()
        if len(group.members) < assignment.max_group_size:
            group.invited_members.remove(user.key)
            group.members.append(user.key)
            group.put()
        else:
            raise BadValueError("too many people in group")

    def reject_invitation(self, group, user):
        # can only reject an invitation if you are in the invited_members
        need = Need('invitation')
        if not group.can(user, need, group):
            raise need.exception()
        group.invited_members.remove(user.key)
        group.put()
