"""The public API."""

#pylint: disable=no-member,unused-argument

import datetime
import logging
import ast
import requests

from flask.views import View
from flask.app import request, json
from flask import session, make_response, redirect
from webargs import Arg
from webargs.flaskparser import FlaskParser
from app.constants import STUDENT_ROLE, STAFF_ROLE, API_PREFIX

from app import models, app, analytics
from app.codereview import compare
from app.needs import Need
from app.utils import paginate, filter_query, create_zip
from app.utils import add_to_grading_queues, parse_date, assign_submission
from app.utils import merge_user

from app.exceptions import *

from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.ext.ndb import stats
from google.appengine.api import memcache


parser = FlaskParser()


def parse_json_field(field):
    """
    Parses field or returns appropriate boolean value.

    :param field: (string)
    :return: (string) parsed JSON
    """
    if not field[0] == '{':
        if field == 'false':
            return False
        elif field == 'true':
            return True
        return field
    return json.loads(field)

def parse_json_list_field(field):
    """
    Parses field or returns appropriate boolean value.

    :param field: (string)
    :return: (string) parsed JSON
    """
    if not field[0] == '[':
        if field == 'false':
            return False
        elif field == 'true':
            return True
        return field
    return json.loads(field)
# Arguments to convert query strings to a python type

def DateTimeArg(**kwds):
    """
    Converts a webarg to a datetime object

    :param kwds: (dictionary) set of parameters
    :return: (Arg) type of argument
    """
    def parse_date(arg):
        op = None
        if '|' in arg:
            op, arg = arg.split('|', 1)

        date = datetime.datetime.strptime(arg,
                                          app.config['GAE_DATETIME_FORMAT'])
        delta = datetime.timedelta(hours=7)
        date = (datetime.datetime.combine(date.date(), date.time()) + delta)
        return (op, date) if op else date
    return Arg(None, use=parse_date, **kwds)

MODEL_VERSION = 'v2'

def try_int(x):
    try:
        return int(x)
    except (ValueError, TypeError):
        return x

def KeyArg(cls, **kwds):
    """
    Converts a webarg to a key in Google's ndb.

    :param cls: (string) class
    :param kwds: (dictionary) -- unused --
    :return: (Arg) type of argument
    """
    def parse_key(key):
        key = try_int(key)
        return {'pairs': [(cls + MODEL_VERSION, key)]}
    return Arg(ndb.Key, use=parse_key, **kwds)


def KeyRepeatedArg(cls, **kwds):
    """
    Converts a repeated argument to a list

    :param cls: (string)
    :param kwds: (dictionary) -- unused --
    :return: (Arg) type of argument
    """
    def parse_list(key_list):
        staff_lst = key_list
        if not isinstance(key_list, list):
            if ',' in key_list:
                staff_lst = key_list.split(',')
                staff_lst = map(try_int, staff_lst)
            else:
                staff_lst = [try_int(key_list)]
        return [ndb.Key(cls + MODEL_VERSION, x) for x in staff_lst]
    return Arg(None, use=parse_list, **kwds)


def BooleanArg(**kwargs):
    """
    Converts a webarg to a boolean.

    :param kwargs: (dictionary) -- unused --
    :return: (Arg) type of argument
    """
    def parse_bool(arg):
        if isinstance(arg, bool):
            return arg
        if arg == 'false':
            return False
        if arg == 'true':
            return True
        raise BadValueError(
            "malformed boolean %s: either 'true' or 'false'" % arg)
    return Arg(None, use=parse_bool, **kwargs)


class APIResource(View):
    """
    Base class for API Resource. Set models for each.
    """

    model = None
    methods = {}
    key_type = int
    api_version = 'v1'

    @property
    def name(self):
        return self.model.__name__

    def get_instance(self, key, user):
        """
        Get instance of the object, checking against user privileges.

        :param key: (int) ID of object
        :param user: (object) user object
        :return: (object, Exception)
        """
        obj = self.model.get_by_id(key)
        if not obj:
            raise BadKeyError(key)

        need = Need('get')
        if not obj.can(user, need, obj):
            raise need.exception()
        return obj

    def call_method(self, method_name, user, http_method,
                    instance=None, is_index=False):
        """
        Call method if it exists and if it's properly called.

        :param method_name: (string) name of desired method
        :param user: (object) caller
        :param http_method: (string) get, post, put, or delete
        :param instance: (string)
        :param is_index: (bool) whether or not this is an index call
        :return: result of called method
        """
        if method_name not in self.methods:
            raise BadMethodError('Unimplemented method %s' % method_name)
        constraints = self.methods[method_name]
        if 'methods' in constraints:
            if http_method is None:
                raise IncorrectHTTPMethodError('Need to specify HTTP method')
            if http_method not in constraints['methods']:
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
        """
        "Does the request dispatching. Matches the URL and returns
        the return value of the view or error handler. This does
        not have to be a response object."
        - http://flask.pocoo.org/docs/0.10/api/

        :param path: (string) full URL
        :param args: (list)
        :param kwargs: (dictionary)
        :return: result of an attempt to call method
        """
        http_method = request.method.upper()
        user = session['user']

        if path is None:  # Index
            if http_method not in ('GET', 'POST'):
                raise IncorrectHTTPMethodError('Incorrect HTTP method: %s')
            method_name = {'GET': 'index', 'POST': 'post'}[http_method]
            return self.call_method(method_name, user, http_method,
                                    is_index=(method_name == 'index'))

        path = path.split('/')
        if len(path) == 1:
            entity_id = path[0]
            try:
                key = self.key_type(entity_id)
            except (ValueError, AssertionError):
                raise BadValueError('Invalid key. Needs to be of type: %s'
                                    % self.key_type)
            instance = self.get_instance(key, user)
            method_name = http_method.lower()
            return self.call_method(method_name, user, http_method,
                                    instance=instance)

        entity_id, method_name = path
        try:
            key = self.key_type(entity_id)
        except (ValueError, AssertionError):
            raise BadValueError('Invalid key. Needs to be of type: %s'
                                % self.key_type)
        instance = self.get_instance(key, user)
        return self.call_method(method_name, user, http_method,
                                instance=instance)

    def get(self, obj, user, data):
        """
        GET HTTP method

        :param obj: (object) target
        :param user: -- unused --
        :param data: -- unused --
        :return: target object
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
                return 400, '{} is not a valid field.'.format(key)

            setattr(obj, key, value)
            changed = True

        if changed:
            obj.put()

        return obj

    def post(self, user, data):
        """
        PUT HTTP method

        :param obj: (object) target
        :param user: (object) caller
        :param data: -- unused --
        :return: target
        """
        entity = self.new_entity(data)

        need = Need('create')
        if not self.model.can(user, need, obj=entity):
            raise need.exception()

        entity.put()

        return (201, 'success', {
            'key': entity.key.id()
        })

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.

        :param attributes: (dictionary)
        :return: (entity, error_response) should be ignored if error_response
        is a True value
        """
        return self.model.from_dict(attributes)

    def delete(self, obj, user, data):
        """
        DELETE HTTP method

        :param obj: (object) target
        :param user: (object) caller
        :param data: -- unused --
        :return: None
        """
        need = Need('delete')
        if not self.model.can(user, need, obj=obj):
            raise need.exception()

        obj.key.delete()

    def parse_args(self, web_args, user, is_index=False):
        """
        Parses the arguments to this API call.

        :param web_args: (string) arguments passed as querystring
        :param user: (object) caller
        :param is_index: (bool) whether or not this is an index call
        :return: (dictionary) mapping keys to values in web arguments
        """
        fields = parser.parse({
            'fields': Arg(None, use=parse_json_field)
        })
        if fields['fields'] is None:
            fields['fields'] = {}
        if type(fields['fields']) != dict and type(fields['fields']) != bool:
            raise BadValueError('fields should be dictionary or boolean')
        request.fields = fields
        return {k: v for k, v in parser.parse(web_args).iteritems()
                if v is not None}

    def index(self, user, data):
        """
        Index HTTP method. Should be called from GET when no key is provided.

        Processes cursor and num_page URL arguments for pagination support.

        :param user: (object) caller
        :param data: (dictionary)
        :return: results for query
        """
        query = self.model.query()
        need = Need('index')

        result = self.model.can(user, need, query=query)
        if not result:
            raise need.exception()

        query = filter_query(result, data, self.model)
        created_prop = getattr(self.model, 'created', None)
        if not query.orders and created_prop:
            logging.info('Adding default ordering by creation time.')
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
        """
        Provide statistics for any entity.

        :return: (dictionary) empty or a 'total' count
        """
        stat = stats.KindStat.query(
            stats.KindStat.kind_name == self.model.__name__).get()
        if stat:
            return {
                'total': stat.count
            }
        return {}


class UserAPI(APIResource):
    """
    The API resource for the User Object
    """
    model = models.User
    key_type = str # get_instance will convert this to an int

    methods = {
        'post': {
            'web_args': {
                'email': Arg(str),
                'name': Arg(str),
                }
        },
        'add_email': {
            'methods': set(['PUT']),
            'web_args': {
                'email': Arg(str)
            }
        },
        'delete_email': {
            'methods': set(['PUT']),
            'web_args': {
                'email': Arg(str)
            }
        },
        'get': {
            'web_args': {
                'course': KeyArg('Course')
             }
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
        },
        'get_backups': {
            'methods': set(['GET']),
            'web_args': {
                'assignment': KeyArg('Assignment', required=True),
                'quantity': Arg(int, default=10)
            }
        },
        'get_submissions': {
            'methods': set(['GET']),
            'web_args': {
                'assignment': KeyArg('Assignment', required=True),
                'quantity': Arg(int, default=10)
            }
        },
        'merge_user': {
            'methods': set(['POST']),
            'web_args': {
                'other_email': Arg(str, required=True),
            }
        },
    }

    def get(self, obj, user, data):
        """
        Overwrite GET request for user class in order to send more data.

        :param obj: (object) target
        :param user: -- unused --
        :param data: -- unused --
        :return: target object
        """
        if 'course' in data:
            return obj.get_course_info(data['course'].get())
        return obj

    def get_instance(self, key, user):
        """
        Convert key from email to UserKey
        """
        obj = self.model.lookup(key)
        if not obj:
            raise BadKeyError(key)

        need = Need('get')
        if not obj.can(user, need, obj):
            raise need.exception()

        return obj

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.

        :param attributes: (dictionary) default values
            loaded on object instantiation
        :return: entity with loaded attributes
        """
        entity = self.model.lookup(attributes['email'])
        if entity:
            raise BadValueError('user already exists')
        attributes['email'] = [attributes['email']]
        entity = self.model.from_dict(attributes)
        return entity

    def add_email(self, obj, user, data):
        """
        Adds an email for the user - modified in place.

        :param obj: (object) target
        :param user: (object) caller
        :param data: -- unused --
        :return: None
        """
        need = Need('get') # Anyone who can get the User object can add an email
        if not obj.can(user, need, obj):
            raise need.exception()
        obj.append_email(data['email'])

    def delete_email(self, obj, user, data):
        """
        Deletes an email for the user - modified in place.

        :param obj: (object) target
        :param user: (object) caller
        :param data: (dictionary) key "email" deleted
        :return: None
        """
        need = Need('get')
        if not obj.can(user, need, obj):
            raise need.exception()
        obj.delete_email(data['email'])

    def invitations(self, obj, user, data):
        """
        Fetches list of all invitations for the caller.

        :param obj: -- unused --
        :param user: (object) caller
        :param data: (dictionary) key assignment called
        :return: None
        """
        query = models.Group.query(models.Group.invited == user.key)
        if 'assignment' in data:
            query = query.filter(models.Group.assignment == data['assignment'])
        return list(query)

    def queues(self, obj, user, data):
        """
        Retrieve all assignments given to the caller on staff

        :param obj: -- unused --
        :param user: (object) caller
        :param data: -- unused --
        :return: None
        """
        return list(models.Queue.query().filter(
            models.Queue.assigned_staff == user.key))

    def create_staff(self, obj, user, data):
        """
        Checks the caller is on staff, to then create staff.

        :param obj: (object) target
        :param user: (object) caller
        :param data: (dictionary) key email called
        :return: None
        """
        need = Need('staff')
        if not obj.can(user, need, obj):
            raise need.exception()

        user = models.User.get_or_insert(data['email'].id())
        user.role = data['role']
        user.put()

    def final_submission(self, obj, user, data):
        """
        Get the final submission for grading.

        :param obj: -- unused --
        :param user: (object) caller
        :param data: (dictionary) key assignment called
        :return: None
        """
        return obj.get_final_submission(data['assignment'])

    def get_backups(self, obj, user, data):
        """
        Get all backups for a user, based on group.

        :param obj: -- unused --
        :param user: (object) caller
        :param data: (dictionary) key assignment called
        :return: None
        """
        return obj.get_backups(data['assignment'], data['quantity'])

    def get_submissions(self, obj, user, data):
        return obj.get_submissions(data['assignment'], data['quantity'])

    def merge_user(self, obj, user, data):
        """
        Merges this user with another user.
        This user is the user that is "merged" -- no longer can login.
        """
        need = Need('merge')
        if not obj.can(user, need, obj):
            raise need.exception()

        other_user = models.User.lookup(data['other_email'])
        if not other_user:
            raise BadValueError("Invalid user to merge to")

        merge_user(obj, other_user)


class AssignmentAPI(APIResource):
    """
    The API resource for the Assignment Object
    """
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
        'invite': {
            'methods': set(['POST']),
            'web_args': {
                'email': Arg(str, required=True)
            }
        },
        'group': {
          'methods': set(['GET']),
        },
        'assign': {
            'methods': set(['POST'])
        }
    }

    def post(self, user, data):
        """
        :param user:
        :param data:
        :return:
        """
        data['creator'] = user.key
        # check if the course actually exists
        course = data['course'].get()
        if not course:
            raise BadValueError("Course with ID {} does not exist.".format(
                data['course'].id()))

        # check if there is a duplicate assignment
        assignments = list(
            models.Assignment.query(models.Assignment.name == data['name']))
        if len(assignments) > 0:
            raise BadValueError(
                'assignment with name %s exists already' % data['name'])
        return super(AssignmentAPI, self).post(user, data)

    def assign(self, obj, user, data):
        need = Need('put')
        if not obj.can(user, need, obj):
            raise need.exception()
        deferred.defer(add_to_grading_queues, obj.key)

    def group(self, obj, user, data):
        """User's current group for assignment."""
        return models.Group.lookup(user, obj)

    def invite(self, obj, user, data):
        """User ask invited to join his/her current group for assignment."""
        err = models.Group.invite_to_group(user.key, data['email'], obj.key)
        if err:
            raise BadValueError(err)


class SubmitNDBImplementation(object):
    """
    Implementation of DB calls required by submission using Google NDB
    """

    def lookup_assignments_by_name(self, name):
        """
        Look up all assignments of a given name.

        :param name: (string) name to search for
        :return: (list) assignments
        """
        mc_key = 'assignments_{}'.format(name)
        assignments = memcache.get(mc_key)
        if not assignments:
            by_name = models.Assignment.name == name
            assignments = list(models.Assignment.query().filter(by_name))
            memcache.set(mc_key, assignments)
        return assignments

    def create_submission(self, user, assignment, messages, submit, submitter):
        """
        Create submission using user as parent to ensure ordering.

        :param user: (object) caller
        :param assignment: (Assignment)
        :param messages: Data content of backup/submission
        :param submit: Whether this backup is a submission to be graded
        :param submitter: (object) caller or submitter
        :return: (Backup) submission
        """
        if not user.is_admin or not submitter:
            submitter = user.key

        message_date = None
        analytics = messages.get('analytics')
        if analytics:
            message_date = analytics.get('time', None)
        if message_date:
            created = parse_date(message_date)
        else:
            created = datetime.datetime.now()

        ms = lambda kind, message: models.Message(kind=kind, contents=message)
        db_messages = [ms(k, m) for k, m in messages.iteritems() if m]

        backup = models.Backup(submitter=submitter,
                               assignment=assignment.key,
                               messages=db_messages,
                               created=created)
        backup.put()
        deferred.defer(assign_submission, backup.key.id(), submit)
        return backup


class SubmissionAPI(APIResource):
    """
    The API resource for the Backup & Submission Objects
    """
    model = models.Backup
    diff_model = models.Diff

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
            'methods': set(['GET']),
            },
        'download': {
            'methods': set(['GET']),
            },
        'add_comment': {
            'methods': set(['POST']),
            'web_args': {
                'index': Arg(int, required=True),
                'file': Arg(str, required=True),
                'message': Arg(str, required=True)
            }
        },
        'delete_comment': {
            'methods': set(['POST']),
            'web_args': {
                'comment': KeyArg('Comment', required=True)
            }
        },
        'add_tag': {
            'methods': set(['PUT']),
            'web_args': {
                'tag': Arg(str, required=True)
            }
        },
        'remove_tag': {
            'methods': set(['PUT']),
            'web_args': {
                'tag': Arg(str, required=True)
            }
        },
        'win_rate': {
            'methods': set(['GET']),
        }
    }

    def graded(self, obj, user, data):
        """
        Gets the user's graded submissions

        :param obj: (object) target
        :param user: (object) caller
        :param data: (dictionary) data
        :return:
        """

    def download(self, obj, user, data):
        """
        Download submission, but check if it has content and encode all files.

        :param obj: (object) target
        :param user: (object) caller
        :param data: (dictionary) data
        :return: file contents in utf-8
        """
        messages = obj.get_messages()
        if 'file_contents' not in messages:
            raise BadValueError('Submission has no contents to download')
        file_contents = messages['file_contents']

        if 'submit' in file_contents:
            del file_contents['submit']

        # Need to encode every file before it is.
        for key in file_contents.keys():
            try:
                file_contents[key] = file_contents[key].encode('utf-8')
            except:
                pass
        response = make_response(create_zip(file_contents))

        response.headers['Content-Disposition'] = (
            'attachment; filename=submission-%s.zip' % str(obj.created))
        response.headers['Content-Type'] = 'application/zip'
        return response

    def diff(self, obj, user, data):
        """
        Gets the associated diff for a submission

        :param obj: (object) target
        :param user: -- unused --
        :param data: -- unused --
        :return: (Diff) object with differences
        """
        messages = obj.get_messages()
        if 'file_contents' not in obj.get_messages():
            raise BadValueError('Submission has no contents to diff')

        file_contents = messages['file_contents']

        if 'submit' in file_contents:
            del file_contents['submit']

        for key in file_contents.keys():
            try:
                file_contents[key] = file_contents[key].encode('utf-8')
            except:
                pass

        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if diff_obj:
            return diff_obj

        diff = {}
        templates = obj.assignment.get().templates
        if not templates or templates == {}:
            raise BadValueError('no templates for assignment, \
                                please contact course staff')

        templates = json.loads(templates)
        if type(templates) == unicode:
            templates = ast.literal_eval(templates)

        for filename, contents in file_contents.items():
            if filename in templates:
                temp = templates[filename]
                if type(templates[filename]) == list:
                    temp = templates[filename][0]
            else:
                temp = ""
            diff[filename] = compare.diff(temp, contents)

        diff = self.diff_model(id=obj.key.id(),
                               diff=diff)
        diff.put()
        return diff

    def add_comment(self, obj, user, data):
        """
        Adds a comment to this diff.

        :param obj: (object) target
        :param user: (object) caller
        :param data: (dictionary) data
        :return: result of putting comment
        """
        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if not diff_obj:
            raise BadValueError("Diff doesn't exist yet")

        index = data['index']
        message = data['message']
        filename = data['file']

        if message.strip() == '':
            raise BadValueError('Cannot make empty comment')

        comment = models.Comment(
            filename=filename,
            message=message,
            line=index,
            author=user.key,
            parent=diff_obj.key)
        comment.put()
        return comment

    def delete_comment(self, obj, user, data):
        """
        Deletes a comment on this diff.

        :param obj: (object) target
        :param user: (object) caller
        :param data: (dictionary) data
        :return: result of deleting comment
        """
        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if not diff_obj:
            raise BadValueError("Diff doesn't exist yet")

        comment = models.Comment.get_by_id(
            data['comment'].id(), parent=diff_obj.key)
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

        :param obj: (object) target
        :param user: -- unused --
        :param data: (dictionary) data
        :return: result of adding tag
        """
        tag = data['tag']
        if tag in obj.tags:
            raise BadValueError('Tag already exists')

        submit_tag = models.Submission.SUBMITTED_TAG
        if tag == submit_tag:
            previous = models.Submission.query().filter(
                models.Submission.assignment == obj.assignment).filter(
                    models.Submission.submitter == obj.submitter).filter(
                        models.Submission.tags == submit_tag)

            previous = previous.get(keys_only=True)
            if previous:
                raise BadValueError('Only one final submission allowed')

        obj.tags.append(tag)
        obj.put()

    def remove_tag(self, obj, user, data):
        """
        Adds a tag to this submission.
        Validates uniqueness.

        :param obj: (object) target
        :param user: (object) caller
        :param data: (dictionary) data
        :return: result of removing tag
        """
        tag = data['tag']
        if tag not in obj.tags:
            raise BadValueError('Tag does not exist.')

        obj.tags.remove(tag)
        obj.put()

    def win_rate(self, obj, user, data):
        """
        Gets the win_rate for the submission. This method will be removed shortly.

        :param obj: (object) target
        :param user: -- unused --
        :param data: -- unused --
        :return: Reponse from Autograder.
        """
        messages = obj.get_messages()
        if 'file_contents' not in obj.get_messages():
            raise BadValueError('Submission has no contents to diff')
        file_contents = messages['file_contents']

        if 'hog.py' not in file_contents:
            raise BadValueError('Submission is not for Hog')
        cached = memcache.get('%s:hog_win' % obj.key.id())
        if cached is not None:
          return cached
        else:
          hog_code = file_contents['hog.py'].encode('utf-8')
          payload = {'strategy': hog_code}
          headers={'content-type': 'application/json'}
          q = requests.post('http://hog.cs61a.org/winrate',
             data=json.dumps(payload),
             headers=headers)
          memcache.add('%s:hog_win' % obj.key.id(), q.json(), 86400)
          return q.json()


    def score(self, obj, user, data):
        """
        Sets composition score

        :param obj: (object) target
        :param user: (object) caller
        :param data: (dictionary) data
        :return: (int) score
        """
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
        """
        Look up an assignment by name

        :param name: (string) name of assignment
        :return: (object, Error) the assignment object or
            raise a validation error
        """
        assignments = self.db.lookup_assignments_by_name(name)

        if not assignments:
            raise BadValueError('Assignment \'%s\' not found' % name)
        if len(assignments) > 1:
            raise BadValueError('Multiple assignments named \'%s\'' % name)
        return assignments[0]

    def submit(self, user, assignment, messages, submit, submitter=None):
        """
        Process submission messages for an assignment from a user.
        """
        valid_assignment = self.get_assignment(assignment)

        if submitter is None:
            submitter = user.key

        due = valid_assignment.due_date
        late_flag = valid_assignment.lock_date and \
                    datetime.datetime.now() >= valid_assignment.lock_date
        revision = valid_assignment.revision

        if submit and late_flag:
            if revision:
                # In the revision period. Ensure that user has a previously graded submission.
                fs = user.get_final_submission(valid_assignment)
                if fs is None or fs.submission.get().score == []:
                    logging.info('Rejecting Revision without graded FS', submitter)
                    return (403, 'Previous submission was not graded', {
                      'late': True,
                      })
            else:
                # Late submission. Do not allow them to submit
                logging.info('Rejecting Late Submission', submitter)
                return (403, 'late', {
                    'late': True,
                    })


        models.Participant.add_role(user, valid_assignment.course, STUDENT_ROLE)
        submission = self.db.create_submission(user, valid_assignment,
                                               messages, submit, submitter)
        return (201, 'success', {
            'key': submission.key.id(),
            'course': valid_assignment.course.id(),
            'email': user.email[0]
        })

    def post(self, user, data):
        submit_flag = False
        if data['messages'].get('file_contents'):
            if 'submit' in data['messages']['file_contents']:
                submit_flag = data['messages']['file_contents']['submit']

        return self.submit(user, data['assignment'],
                           data['messages'], submit_flag,
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
            raise BadValueError('Duplicate version: {}'.format(new_version))

        obj.versions.append(new_version)
        if 'current' in data and data['current']:
            obj.current_version = data['version']
        obj.put()
        return obj

    def current(self, obj, user, data):
        need = Need('get')
        if not obj.can(user, need, obj):
            raise need.exception()
        if not obj.current_version:
            raise BadValueError(
                'Invalid version resource. Contact an administrator.')
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
            raise BadValueError(
                'Invalid version. Cannot update to current.')
        obj.current_version = current_version
        obj.put()


class CourseAPI(APIResource):
    model = models.Course

    methods = {
        'post': {
            'web_args': {
                'display_name': Arg(str),
                'institution': Arg(str, required=True),
                'offering': Arg(str, required=True),
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
                'email': Arg(str, required=True)
            }
        },
        'remove_staff': {
            'methods': set(['POST']),
            'web_args': {
                'email': Arg(str, required=True)
            }
        },
        'assignments': {
            'methods': set(['GET']),
            'web_args': {
            }
        },
        'get_courses': {
            'methods': set(['GET']),
            'web_args': {
                'user': KeyArg('User', required=True)
            }
        },
        'get_students': {
        },
        'add_student': {
            'methods': set(['POST']),
            'web_args': {
                'student': KeyArg('User', required=True)
            }
        },
        }

    def post(self, user, data):
        """
        The POST HTTP method
        """
        return super(CourseAPI, self).post(user, data)

    def add_staff(self, course, user, data):
        need = Need('staff')
        if not course.can(user, need, course):
            raise need.exception()

        user = models.User.get_or_insert(data['email'])
        if user not in course.staff:
          models.Participant.add_role(user, course, STAFF_ROLE)

    def get_staff(self, course, user, data):
        need = Need('staff')
        if not course.can(user, need, course):
            raise need.exception()
        query = models.Participant.query(
          models.Participant.course == course.key,
          models.Participant.role == 'staff')
        return list(query.fetch())

    def remove_staff(self, course, user, data):
        need = Need('staff')
        if not course.can(user, need, course):
            raise need.exception()

        removed_user = models.User.lookup(data['email'])
        if removed_user:
          models.Participant.remove_role(removed_user, course, STAFF_ROLE)

    def get_courses(self, course, user, data):
        query = models.Participant.query(
            models.Participant.user == data['user'])
        need = Need('index')
        query = models.Participant.can(user, need, course, query)
        return list(query)


    def get_students(self, course, user, data):
        query = models.Participant.query(
            models.Participant.course == course.key)
        need = Need('staff')
        if not models.Participant.can(user, need, course, query):
            raise need.exception()
        return list(query.fetch())

    def add_student(self, course, user, data):
        need = Need('staff') # Only staff can call this API
        if not course.can(user, need, course):
            raise need.exception()
        new_participant = models.Participant.add_role(user, course, STUDENT_ROLE)
        new_participant.put()

    def assignments(self, course, user, data):
        return list(course.assignments)


class GroupAPI(APIResource):
    model = models.Group

    methods = {
        'get': {
        },
        'index': {
            'web_args': {
                'assignment': KeyArg('Assignment'),
                'members': KeyArg('User')
            }
        },
        'add_member': {
            'methods': set(['PUT', 'POST']),
            'web_args': {
                'email': Arg(str, required=True),
                },
            },
        'remove_member': {
            'methods': set(['PUT', 'POST']),
            'web_args': {
                'email': Arg(str, required=True),
                },
            },
        'accept': {
            'methods': set(['PUT', 'POST']),
            },
        'decline': {
            'methods': set(['PUT', 'POST']),
            },
        'exit': {
            'methods': set(['PUT', 'POST']),
            }
    }

    def add_member(self, group, user, data):
        need = Need('invite')
        if not group.can(user, need, group):
            raise need.exception()

        if data['email'] in group.invited:
            raise BadValueError('user has already been invited')
        if data['email'] in group.member:
            raise BadValueError('user already part of group')

        error = group.invite(data['email'])
        if error:
            raise BadValueError(error)

        audit_log_message = models.AuditLog(
            event_type='Group.add_member',
            user=user.key,
            description='Added member {} to group'.format(data['email']),
            obj=group.key
        )
        audit_log_message.put()

    def remove_member(self, group, user, data):
        need = Need('remove')
        if not group.can(user, need, group):
            raise need.exception()

        to_remove = models.User.lookup(data['email'])
        if to_remove:
            group.exit(to_remove)

            audit_log_message = models.AuditLog(
                event_type='Group.remove_member',
                user=user.key,
                obj=group.key,
                description='Removed user from group'
            )
            audit_log_message.put()

    def invite(self, group, user, data):
        need = Need('invite')
        if not group.can(user, need, group):
            return need.exception()

        error = group.invite(data['email'])
        if error:
            raise BadValueError(error)

    def accept(self, group, user, data):
        need = Need('accept')
        if not group.can(user, need, group):
            raise need.exception()

        group.accept(user)

    def decline(self, group, user, data):
        self.exit(group, user, data)

    def exit(self, group, user, data):
        need = Need('exit')
        if not group.can(user, need, group):
            raise need.exception()

        group.exit(user)


class QueueAPI(APIResource):
    """
    The API resource for the Assignment Object
    """
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
                'assignment': KeyArg('Assignment'),
                'assigned_staff': KeyArg('User'),
                'owner': KeyArg('User'),
            }
        },
        }

    def new_entity(self, attributes):
        """
        Request to define a new entity

        :param attributes: entity attributes,
            to be loaded on entity instantiation
        :return: entity
        """
        if 'owner' not in attributes:
            attributes['owner'] = attributes['assigned_staff'][0]
        ent = super(QueueAPI, self).new_entity(attributes)
        ent.assigned_staff = [models.User.get_or_insert(
            user.id()).key for user in ent.assigned_staff]
        return ent

class FinalSubmissionAPI(APIResource):
    """
    The API resource for the Assignment Object
    """
    model = models.FinalSubmission

    methods = {
        'get': {
        },
        'index': {
        },
        'score': {
            'methods': set(['POST']),
            'web_args': {
                'score': Arg(int, required=True),
                'message': Arg(str, required=True),
                'source': Arg(str, required=True),
              }
        }

        }

    def score(self, obj, user, data):
        """
        Sets composition score

        :param obj: (object) target
        :param user: (object) caller
        :param data: (dictionary) data
        :return: (int) score
        """
        need = Need('grade')
        if not obj.can(user, need, obj):
            raise need.exception()

        score = models.Score(
            score=data['score'],
            message=data['message'],
            grader=user.key)
        grade = score.put()

        submission = obj.submission.get()

        # Create or updated based on existing scores.
        if data['source'] == 'composition':
          # Only keep any autograded scores.
          submission.score = [autograde for autograde in submission.score \
            if score.autograder]
          submission.score.append(score)
        else:
          submission.score.append(score)

        submission.put()

        return score

class AnalyticsAPI(APIResource):
    """
    The API resource for the AnalyticsDump Object
    """
    model = analytics.AnalyticsDump

    methods = {
        'get': {
        },
        'index': {
        },
        'post': {
            'web_args': {
                'job_type': Arg(str, required=True),
                'filters': Arg(None, use=parse_json_list_field, required=True),
            }
        },
    }

    def post(self, user, data):

        need = Need('create')

        if not self.model.can(user, need, None):
            raise need.exception()

        job_type, filters = data['job_type'], data['filters']

        if not isinstance(filters, list):
            raise BadValueError('filters must be a list of triples')
        for filter in filters:
            if len(filter) != 3:
                raise BadValueError('filters must be a list of triples')

        if job_type not in analytics.available_jobs:
            raise BadValueError('job must be of the following types: %s' %
                                ', '.join(list(analytics.available_jobs.keys())))

        job = analytics.get_job(job_type, user, filters)
        job.start()

        return (201, 'success', {
            'key': job.job_dump.key.id()
        })
