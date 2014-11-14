"""
The public API
"""
import datetime
import logging

from flask.views import View
from flask.app import request, json
from flask import session, make_response, redirect
from webargs import Arg
from webargs.flaskparser import FlaskParser

from app import models, app
from app.codereview import compare
from app.constants import API_PREFIX
from app.needs import Need
from app.utils import paginate, filter_query, create_zip, assign_work, parse_date, assign_submission

from app.exceptions import *

from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.ext.ndb import stats

parser = FlaskParser()

def parse_json_field(field):
    if not field[0] == '{':
        if field == "false":
            return False
        elif field == "true":
            return True
        return field
    return json.loads(field)


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

def BooleanArg(**kwargs):
    def parse_bool(arg):
        if isinstance(arg, bool):
            return arg
        if arg == "false":
            return False
        if arg == "true":
            return True
        raise BadValueError("malformed boolean %s: either 'true' or 'false'" % arg)
    return Arg(None, use=parse_bool, **kwargs)

class APIResource(View):
    """The base class for API resources.

    Set the model for each subclass.
    """

    model = None
    methods = {}
    key_type = int
    api_version = 'v1'

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
        for key, value in data.iteritems():
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

        return (201, "success", {
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

    def parse_args(self, web_args, user, is_index=False):
        """
        Parses the arguments to this API call.
        |index| is whether or not this is an index call.
        """
        fields = parser.parse({
            'fields': Arg(None, use=parse_json_field)
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
        # default page length is 100
        num_page = int(request.args.get('num_page', 100))
        query_results = paginate(query, page, num_page)

        add_statistics = request.args.get('stats', False)
        if add_statistics:
            query_results['statistics'] = self.statistics()
        return query_results

    def statistics(self):
        stat = stats.KindStat.query(stats.KindStat.kind_name == self.model.__name__).get()
        if stat:
            return {
                'total': stat.count
            }
        return {}


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
        'put': {
            'web_args': {
                'first_name': Arg(str),
                'last_name': Arg(str),
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
        'queues': {
            'methods': set(['GET'])
        },
        'create_staff': {
            'methods': set(['POST']),
            'web_args': {
                'email': Arg(str, required=True),
                'role': Arg(str, required=True),
            }
        },
        'final_submission': {
            'methods': set(['GET']),
            'web_args': {
                'assignment': KeyArg('Assignment', required=True)
            }
        }
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

    def invitations(self, obj, user, data):
        query = models.Group.query(models.Group.invited_members == user.key)
        if 'assignment' in data:
            query = query.filter(models.Group.assignment == data['assignment'])
        return list(query)

    def queues(self, obj, user, data):
        return list(models.Queue.query().filter(
            models.Queue.assigned_staff == user.key))

    def create_staff(self, obj, user, data):
        # Must be a staff to create a staff user
        need = Need("staff")
        if not obj.can(user, need, obj):
            raise need.exception()

        user = models.User.get_or_insert(data['email'].id())
        user.role = data['role']
        user.put()


    def final_submission(self, obj, user, data):
        return obj.get_selected_submission(data['assignment'])


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
        'put': {
            'web_args': {
                'name': Arg(str),
                'display_name': Arg(str),
                'points': Arg(float),
                'course': KeyArg('Course'),
                'max_group_size': Arg(int),
                'due_date': DateTimeArg(),
                'templates': Arg(str, use=lambda temps: json.dumps(temps)),
            }
        },
        'get': {
        },
        'index': {
            'web_args': {
                'course': KeyArg('Course'),
                'active': BooleanArg(),
                'name': Arg(str),
                'points': Arg(int)
            }
        },
        'assign': {
            'methods': set(['POST'])
        }
    }

    def post(self, user, data):
        data['creator'] = user.key
        # check if there is a duplicate assignment
        assignments = list(models.Assignment.query(models.Assignment.name == data['name']))
        if len(assignments) > 0:
            raise BadValueError("assignment with name %s exists already" % data["name"])
        return super(AssignmentAPI, self).post(user, data)

    def assign(self, obj, user, data):
        # Todo: Should make this have permissions! 
        # need = Need('staff')
        # if not obj.can(user, need, obj):
        #     raise need.exception()
        deferred.defer(assign_work, obj.key)


class SubmitNDBImplementation(object):
    """Implementation of DB calls required by submission using Google NDB"""

    def lookup_assignments_by_name(self, name):
        """Look up all assignments of a given name."""
        by_name = models.Assignment.name == name
        return list(models.Assignment.query().filter(by_name))

    def create_submission(self, user, assignment, messages, submit, submitter):
        """Create submission using user as parent to ensure ordering."""
        if not user.is_admin:
            submitter = user.key
        # TODO - Choose member of group if the user is an admin. 

        db_messages = []
        for kind, message in messages.iteritems():
            if message:
                db_messages.append(models.Message(kind=kind, contents=message))

        created = datetime.datetime.now()
        if messages.get('analytics'):
            date = messages['analytics']['time']
            if date:
                created = parse_date(date)

        submission = models.Submission(submitter=submitter,
                                       assignment=assignment.key,
                                       messages=db_messages,
                                       created=created)
        if submit:
            submission.tags = [models.Submission.SUBMITTED_TAG]
        submission.put()
        deferred.defer(assign_submission, submission.key.id())

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
                'submit': BooleanArg(),
                'submitter': KeyArg('User')
            }
        },
        'get': {
            'web_args': {
            }
        },
        'index': {
            'web_args': {
                'assignment': KeyArg('Assignment'),
                'submitter': KeyArg('User'),
                'created': DateTimeArg(),
                'messages.kind': Arg(str, use=parse_json_field),
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
        'add_tag': {
            'methods': set(["PUT"]),
            'web_args': {
                'tag': Arg(str, required=True)
            }
        },
        'remove_tag': {
            'methods': set(["PUT"]),
            'web_args': {
                'tag': Arg(str, required=True)
            }
        },
        'score': {
            'methods': set(["POST"]),
            'web_args': {
                'score': Arg(int, required=True),
                'message': Arg(str, required=True),
            }
        }
    }

    def get_instance(self, key, user):
        try:
            return super(SubmissionAPI, self).get_instance(key, user)
        except BadKeyError:
            pass

        old_obj = models.OldSubmission.get_by_id(key)
        if not old_obj:
            raise BadKeyError(key)
        obj = old_obj.upgrade()
        obj.put()
        old_obj.key.delete()

        need = Need('get')
        if not obj.can(user, need, obj):
            raise need.exception()
        return obj

    def graded(self, obj, user, data):
        """
        Gets the users graded submissions
        """

    def download(self, obj, user, data):
        """
        Allows you to download a submission.
        """
        messages = obj.get_messages()
        if 'file_contents' not in messages:
            raise BadValueError("Submission has no contents to download")
        file_contents = messages['file_contents']
        
        try:
            response = make_response(create_zip(file_contents))
        except:
            response = make_response(create_zip(file_contents.decode('utf-8')))

        response.headers["Content-Disposition"] = (
            "attachment; filename=submission-%s.zip" % str(obj.created))
        response.headers["Content-Type"] = "application/zip"
        return response

    def diff(self, obj, user, data):
        """
        Gets the associated diff for a submission
        """
        messages = obj.get_messages()
        if 'file_contents' not in obj.get_messages():
            raise BadValueError("Submission has no contents to diff")

        file_contents = messages['file_contents']

        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if diff_obj:
            return diff_obj

        diff = {}
        templates = obj.assignment.get().templates
        if not templates:
            raise BadValueError("no templates for assignment, \
                                please contact course staff")

        templates = json.loads(templates)
        for filename, contents in file_contents.items():
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

        comment = models.Comment.get_by_id(data['comment'].id(), parent=diff_obj.key)
        if not comment:
            raise BadKeyError(data['comment'])
        need = Need('delete')
        if not comment.can(user, need, comment):
            raise need.exception()
        comment.key.delete()

    def add_tag(self, obj, user, data):
        """
        Removes a tag from the submission.
        Validates existence.
        """
        tag = data['tag']
        if tag in obj.tags:
            raise BadValueError("Tag already exists")

        if tag == models.Submission.SUBMITTED_TAG:
            previous = models.Submission.query().filter(
                models.Submission.assignment == obj.assignment).filter(
                    models.Submission.submitter == obj.submitter).filter(
                        models.Submission.tags == models.Submission.SUBMITTED_TAG)

            previous = previous.get(keys_only=True)
            if previous:
                raise BadValueError("Only one final submission allowed")
                # Why not remove the tag from previous submission? 
                # previous.tags.remove(models.Submission.SUBMITTED_TAG)

        obj.tags.append(tag)
        obj.put()

    def remove_tag(self, obj, user, data):
        """
        Adds a tag to this submission.
        Validates uniqueness.
        """
        tag = data['tag']
        if tag not in obj.tags:
            raise BadValueError("Tag does not exists")

        obj.tags.remove(tag)
        obj.put()

    def score(self, obj, user, data):
        score = models.Score(
            score=data['score'],
            message=data['message'],
            grader=user.key)
        score.put()

        if 'Composition' not in obj.tags:
            obj.tags.append('Composition')

        obj.compScore = score.key
        obj.put()
        return score

    def get_assignment(self, name):
        """Look up an assignment by name or raise a validation error."""
        assignments = self.db.lookup_assignments_by_name(name)
        if not assignments:
            raise BadValueError('Assignment \'%s\' not found' % name)
        if len(assignments) > 1:
            raise BadValueError('Multiple assignments named \'%s\'' % name)
        return assignments[0]

    def submit(self, user, assignment, messages, submit, submitter=None):
        """Process submission messages for an assignment from a user."""
        valid_assignment = self.get_assignment(assignment)

        if submitter is None:
            submitter = user.key

        submission = self.db.create_submission(user, valid_assignment,
                                               messages, submit, submitter)
        return (201, "success", {
            'key': submission.key.id()
        })

    def post(self, user, data):
        return self.submit(user, data['assignment'],
                           data['messages'], data.get('submit', False),
                           data.get('submitter'))
    


class VersionAPI(APIResource):
    model = models.Version

    key_type = str

    methods = {
        'post': {
            'web_args': {
                'name': Arg(str, required=True),
                'base_url': Arg(str, required=True),
            }
        },
        'put': {
            'web_args': {
                'name': Arg(str),
                'base_url': Arg(str),
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
        'new': {
            'methods': set(['PUT']),
            'web_args': {
                'version': Arg(str, required=True),
                'current': BooleanArg()
            }
        },
        'download': {
            'methods': set(['GET']),
            'web_args': {
                'version': Arg(str)
            }
        },
        'current': {
            'methods': set(['GET']),
            'web_args': {
            }
        },
        'set_current': {
            'methods': set(['POST']),
            'web_args': {
                'version': Arg(str, required=True)
            }
        },
    }

    def new(self, obj, user, data):
        need = Need('update')
        if not obj.can(user, need, obj):
            raise need.exception()

        new_version = data['version']

        if new_version in obj.versions:
            raise BadValueError("Duplicate version: {}".format(new_version))

        obj.versions.append(new_version)
        if 'current' in data and data['current']:
            obj.current_version = data['current_version']
        obj.put()
        return obj

    def current(self, obj, user, data):
        need = Need('get')
        if not obj.can(user, need, obj):
            raise need.exception()
        if not obj.current_version:
            raise BadValueError("Invalid version resource. Contact an administrator.")
        return obj.current_version

    def download(self, obj, user, data):
        need = Need('get')
        if not obj.can(user, need, obj):
            raise need.exception()
        if 'version' not in data:
            download_link = obj.download_link()
        else:
            download_link = obj.download_link(data['version'])
        return redirect(download_link)


    def set_current(self, obj, user, data):
        need = Need('update')
        if not obj.can(user, need, obj):
            raise need.exception()
        current_version = data['version']
        if current_version not in obj.versions:
            raise BadValueError("Invalid version. Cannot update to current.")
        obj.current_version = current_version
        obj.put()


class CourseAPI(APIResource):
    model = models.Course

    methods = {
        'post': {
            'web_args': {
                'name': Arg(str, required=True),
                'institution': Arg(str, required=True),
                'term': Arg(str, required=True),
                'year': Arg(str, required=True),
                'active': BooleanArg(),
            }
        },
        'put': {
            'web_args': {
                'name': Arg(str),
                'institution': Arg(str),
                'term': Arg(str),
                'year': Arg(str),
                'active': BooleanArg(),
            }
        },
        'delete': {
        },
        'get': {
        },
        'index': {
        },
        'get_staff': {
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

    def get_staff(self, course, user, data):
        need = Need("staff")
        if not course.can(user, need, course):
            raise need.exception()

        return course.staff

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
                'assignment': KeyArg('Assignment', required=True),
                'members': KeyRepeatedArg('User')
            }
        },
        'get': {
        },
        'index': {
            'web_args': {
                'assignment': KeyArg('Assignment'),
                'members': KeyArg('User')
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
        for user_key in data.get('members', ()):
            user = user_key.get()
            if user:
                current_group = list(user.groups(data['assignment']))

                if len(current_group) == 1:
                    raise BadValueError("{} already in a group".format(user_key.id()))
                if len(current_group) > 1:
                    raise BadValueError("{} in multiple groups".format(user_key.id()))
            else:
                models.User.get_or_insert(user_key.id())

        group = self.new_entity(data)
        group.put()


    def add_member(self, group, user, data):
        # can only add a member if you are a member
        need = Need('member')
        if not group.can(user, need, group):
            raise need.exception()

        if data['member'] in group.invited_members:
            raise BadValueError("user has already been invited")
        if data['member'] in group.members:
            raise BadValueError("user already part of group")

        user_to_add = models.User.get_or_insert(data['member'].id())
        group.invited_members.append(user_to_add.key)
        group.put()

        audit_log_message = models.AuditLog(
            event_type='Group.add_member',
            user=user.key,
            description="Added member {} to group".format(data['member']),
            obj=group.key
            )
        audit_log_message.put()

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
            description = "Deleted group"
        else:
            group.put()
            description = "Changed group"

        audit_log_message = models.AuditLog(
            event_type='Group.remove_member',
            user=user.key,
            obj=group.key,
            description=description
            )
        audit_log_message.put()

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

    def reject_invitation(self, group, user, data):
        # can only reject an invitation if you are in the invited_members
        need = Need('invitation')
        if not group.can(user, need, group):
            raise need.exception()
        group.invited_members.remove(user.key)
        group.put()

class QueueAPI(APIResource):
    """The API resource for the Assignment Object"""
    model = models.Queue

    methods = {
        'post': {
            'web_args': {
                'assignment': KeyArg('Assignment', required=True),
                'assigned_staff': KeyRepeatedArg('User'),
                'submissions': KeyRepeatedArg('Submissionvtwo')
            }
        },
        'get': {
        },
        'put': {
            'web_args': {
                'assigned_staff': KeyRepeatedArg('User'),
                'submissions': KeyRepeatedArg('Submissionvtwo')
            }
        },
        'index': {
            'web_args': {
                'assignment': KeyArg('Assigment'),
                'assigned_staff': KeyArg('User'),
            }
        },
    }

    def new_entity(self, attributes):
        ent = super(QueueAPI, self).new_entity(attributes)
        for user in ent.assigned_staff:
            models.User.get_or_insert(user.id())
        return ent
