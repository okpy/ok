"""The public API."""

#pylint: disable=no-member,unused-argument

import datetime
import logging
import ast

from flask.views import View
from flask.app import request, json
from flask import session, make_response, redirect
from webargs import Arg
from webargs.flaskparser import FlaskParser

from app import models, app
from app.codereview import compare
from app.constants import API_PREFIX
from app.needs import Need
from app.utils import paginate, filter_query, create_zip
from app.utils import add_to_grading_queues, parse_date, assign_submission

from app.exceptions import *

from google.appengine.ext import ndb
from google.appengine.ext import deferred
from google.appengine.ext.ndb import stats


parser = FlaskParser()


def parse_json_field(field):
    if not field[0] == '{':
        if field == 'false':
            return False
        elif field == 'true':
            return True
        return field
    return json.loads(field)

# Arguments to convert query strings to a python type

def DateTimeArg(**kwds):
    """Converts a webarg to a datetime object"""
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


def KeyArg(cls, **kwds):
    """Converts a webarg to a key in Google's ndb."""
    def parse_key(key):
        try:
            key = int(key)
        except (ValueError, TypeError):
            pass
        return {'pairs': [(cls, key)]}
    return Arg(ndb.Key, use=parse_key, **kwds)


def KeyRepeatedArg(cls, **kwds):
    """Converts a repeated argument to a list"""
    def parse_list(key_list):
        staff_lst = key_list
        if not isinstance(key_list, list):
            if ',' in key_list:
                staff_lst = key_list.split(',')
            else:
                staff_lst = [key_list]
        return [ndb.Key(cls, x) for x in staff_lst]
    return Arg(None, use=parse_list, **kwds)


def BooleanArg(**kwargs):
    """Converts a webarg to a boolean"""
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
                return 400, '{} is not a valid field.'.format(key)

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

        return (201, 'success', {
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
            raise BadValueError('fields should be dictionary or boolean')
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
        stat = stats.KindStat.query(
            stats.KindStat.kind_name == self.model.__name__).get()
        if stat:
            return {
                'total': stat.count
            }
        return {}


class UserAPI(APIResource):
    """The API resource for the User Object

    model- the class in models.py that this API is for.
    key_type- The type of the id of this model.
    """
    model = models.User
    key_type = str # We will manually convert from email to UserIDs.

    methods = {
        'post': {
            'web_args': {
                'email': KeyRepeatedArg(str, required=True),
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
                'assignment': KeyArg('Assignment', required=True)
            }
        },
        'get_submissions': {
            'methods': set(['GET']),
            'web_args': {
                'assignment': KeyArg('Assignment', required=True)
            }
        }
    }

    def get_instance(self, email, user):
        """
        Override get_instance from the API in order to convert emails to our User model.
        """
        return self.model.lookup(email)

    def get(self, obj, user, data):
        """
        Overwrite GET request for user class in order to send more data.
        """
        if 'course' in data:
            return obj.get_course_info(data['course'].get())
        return obj

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        """
        entity = self.model.lookup(attributes['email'])
        if entity:
            raise BadValueError('user already exists')
        entity = self.model.from_dict(attributes)
        return entity

    def add_email(self, obj, user, data):
        """
        Adds an email for the user (represented by obj).
        """
        need = Need('get') # Anyone who can get the User object can add an email
        if not obj.can(user, need, obj):
            raise need.exception()
        obj.append_email(data['email'])

    def delete_email(self, obj, user, data):
        """
        Deletes an email for the user (represented by obj).
        """
        need = Need('get')
        if not obj.can(user, need, obj):
            raise need.exception()
        obj.delete_email(data['email'])



    def queues(self, obj, user, data):
        return list(models.Queue.query().filter(
            models.Queue.assigned_staff == user.key))

    def create_staff(self, obj, user, data):
        # Must be a staff to create a staff user
        need = Need('staff')
        if not obj.can(user, need, obj):
            raise need.exception()

        user = models.User.get_or_insert(data['email'].id())
        user.role = data['role']
        user.put()

    def final_submission(self, obj, user, data):
        return obj.get_final_submission(data['assignment'])

    def get_backups(self, obj, user, data):
        return obj.get_backups(data['assignment'])

    def get_submissions(self, obj, user, data):
        return obj.get_submissions(data['assignment'])

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
        'grade': {
            'methods': set(['POST'])
        },
        'group': {
            'methods': set(['GET']),
        },
        'invite': {
            'methods': set(['POST']),
            'web_args': {
                'email': Arg(str, required=True)
            }
        },
    }

    def post(self, user, data):
        data['creator'] = user.key
        # check if there is a duplicate assignment
        assignments = list(
            models.Assignment.query(models.Assignment.name == data['name']))
        if len(assignments) > 0:
            raise BadValueError(
                'assignment with name %s exists already' % data['name'])
        return super(AssignmentAPI, self).post(user, data)

    def grade(self, obj, user, data):
        need = Need('grade')
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

        submission = models.Backup(submitter=submitter,
                                       assignment=assignment.key,
                                       messages=db_messages,
                                       created=created)
        submission.put()

        deferred.defer(assign_submission, submission.key.id(), submit)

        return submission


class SubmissionAPI(APIResource):
    """The API resource for the Submission Object"""
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
        'score': {
            'methods': set(['POST']),
            'web_args': {
                'score': Arg(int, required=True),
                'message': Arg(str, required=True),
            }
        }
    }

    def download(self, obj, user, data):
        """
        Allows you to download a submission.
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
            if 'scheme.py' in diff_obj.diff.keys():
                logging.debug('Deleting existing scheme submission')
                diff_obj.key.delete()
            else:
                return diff_obj

        diff = {}
        templates = obj.assignment.get().templates
        if not templates:
            raise BadValueError('no templates for assignment, \
                                please contact course staff')

        templates = json.loads(templates)
        if type(templates) == unicode:
            logging.debug('performing ast')
            templates = ast.literal_eval(templates)

        for filename, contents in file_contents.items():
            temp = templates[filename]
            if type(templates[filename]) == list:
                temp = templates[filename][0]
            diff[filename] = compare.diff(temp, contents)

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

    def delete_comment(self, obj, user, data):
        """
        Deletes a comment on this diff.
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
        """
        tag = data['tag']
        if tag not in obj.tags:
            raise BadValueError('Tag does not exists')

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

        due = valid_assignment.due_date
        late_flag = valid_assignment.lock_date and \
                datetime.datetime.now() >= valid_assignment.lock_date

        if submit and late_flag:
            # Late submission. Do Not allow them to submit
            logging.info('Rejecting Late Submission', submitter)
            return (403, 'late', {
                'late': True,
            })

        submission = self.db.create_submission(user, valid_assignment,
                                               messages, submit, submitter)
        return (201, 'success', {
            'key': submission.key.id()
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
            obj.current_version = data['current_version']
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

        if data['staff_member'] not in course.staff:
            user = models.User.get_or_insert(data['staff_member'].id())
            course.staff.append(user.key)
            course.put()

    def get_staff(self, course, user, data):
        need = Need('staff')
        if not course.can(user, need, course):
            raise need.exception()

        return course.staff

    def remove_staff(self, course, user, data):
        need = Need('staff')
        if not course.can(user, need, course):
            raise need.exception()
        if data['staff_member'] in course.staff:
            course.staff.remove(data['staff_member'])
            course.put()

    def get_students(self, course, user, data):
        return list(models.Participant.query(models.Participant.course == course))

    def add_student(self, course, user, data):
        new_participant = models.Participant(user, course, 'student')
        new_participant.put()

    def assignments(self, course, user, data):
        return list(course.assignments)

class GroupAPI(APIResource):
    """The API resource for Group Object"""
    model = models.Group

    methods = {
        'get': {
        },
        'index': {
        },
        'delete': {
        },
        'invite': {
            'methods': set(['POST']),
            'web_args': {
                'email': Arg(str, required=True)
            }
        },
        'accept': {
            'methods': set(['POST']),
        },
        'exit': {
            'methods': set(['PUT']),
        }
    }

    def invite(self, group, user, data):
        need = Need('invite')
        if not group.can(user, need, group):
            raise need.exception()
        error = group.invite(data['email'])
        if error:
            raise BadValueError(error)

    def accept(self, group, user, data):
        need = Need('accept')
        if not group.can(user, need, group):
            raise need.exception()
        error = group.accept(user)
        if error:
            raise BadValueError(error)

    def exit(self, group, user, data):
        need = Need('exit')
        if not group.can(user, need, group):
            raise need.exception()
        error = group.exit(user)
        if error:
            raise BadValueError(error)

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
                'assignment': KeyArg('Assignment'),
                'assigned_staff': KeyArg('User'),
            }
        },
    }

    def new_entity(self, attributes):
        ent = super(QueueAPI, self).new_entity(attributes)
        for user in ent.assigned_staff:
            models.User.get_or_insert(user.id())
        return ent

class FinalSubmissionAPI(APIResource):
    """The API resource for the FinalSubmission Object"""
    model = models.FinalSubmission

    methods = {
        'get': {
        },
        'index': {
        },
    }
