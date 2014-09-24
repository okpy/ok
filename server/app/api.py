"""
The public API
"""
import logging
import datetime

from flask.views import View
from flask.app import request, json
from flask import session, make_response
from webargs import Arg
from webargs.flaskparser import FlaskParser

from app import models
from app.codereview import compare
from app.constants import API_PREFIX
from app.needs import Need
from app.utils import paginate, filter_query, create_zip

from google.appengine.ext import db, ndb

BadValueError = db.BadValueError

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

    def get_instance(self, key, user):
        obj = self.model.get_by_id(key)
        if not obj:
            return (404, "{resource} {key} not found".format(
                resource=self.name, key=key))

        need = Need('get')
        if not obj.can(user, need, obj):
            return need.api_response()

        return obj

    def dispatch_request(self, path, *args, **kwargs):
        meth = request.method.upper()
        user = session['user']

        if not path: # Index
            if meth == "GET":
                return self.index(user)
            elif meth == "POST":
                return self.post(user)
            assert meth in ("GET", "POST"), 'Unimplemented method %s' % meth

        if '/' not in path:
            # For now, just allow ID gets
            assert meth in ['GET', 'PUT', 'DELETE']
            meth = getattr(self, meth.lower(), None)

            assert meth is not None, 'Unimplemented method %r' % request.method
            try:
                key = self.key_type(path)
            except (ValueError, AssertionError):
                return (400,
                    "Invalid key. Needs to be of type '%s'" % self.key_type)

            inst = self.get_instance(key, user)
            if not isinstance(inst, self.model):
                return inst

            return meth(inst, user, *args, **kwargs)

        entity_id, action = path.split('/')
        try:
            key = self.key_type(entity_id)
        except (ValueError, AssertionError):
            return (400,
                "Invalid key. Needs to be of type '%s'" % self.key_type)

        meth = getattr(self, action, None)
        assert meth is not None, 'Unimplemented action %r' % action
        inst = self.get_instance(key, user)
        if not isinstance(inst, self.model):
            return inst

        return meth(inst, user, *args, **kwargs)

    def get(self, obj, user):
        """
        The GET HTTP method
        """
        return obj

    def put(self, obj, user):
        """
        The PUT HTTP method
        """
        need = Need('put')
        if not obj.can(user, need, obj):
            return need.api_response()

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

    def post(self, user):
        """
        The POST HTTP method
        """
        data = self.parse_args(False, user)

        entity, error_response = self.new_entity(data)
        if error_response:
            return error_response

        need = Need('create')
        if not self.model.can(user, need, obj=entity):
            return need.api_response()

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
        entity = self.model.from_dict(attributes)
        return entity, None

    def delete(self, obj, user):
        """
        The DELETE HTTP method
        """
        need = Need('delete')
        if not self.model.can(user, need, obj=obj):
            return need.api_response()

        obj.key.delete()
        return None

    def parse_args(self, index, user):
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

        return {k:v for k, v in parser.parse(self.web_args).iteritems() if v != None}

    def index(self, user):
        """
        Index HTTP method. Should be called from GET when no key is provided.

        Processes cursor and num_page URL arguments for pagination support.
        """
        query = self.model.query()
        need = Need('index')

        result = self.model.can(user, need, query=query)
        if not result:
            return need.api_response()

        args = self.parse_args(True, user)
        query = filter_query(result, args, self.model)
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

    def new_entity(self, attributes):
        """
        Creates a new entity with given attributes.
        """
        if 'email' not in attributes:
            return None, (400, 'Email required')
        entity = self.model.get_by_id(attributes['email'])
        if entity:
            return None, (400, '%s already exists' % self.name)
        entity = self.model.from_dict(attributes)
        return entity, None

    web_args = {
        'first_name': Arg(str),
        'last_name': Arg(str),
        'email': Arg(str),
        'login': Arg(str),
        'assignment': Arg(int),
        'invitation': Arg(int),
        'course': KeyArg('User'),
    }

    def invitations(self, user, obj):
        data = self.parse_args(False, user)
        query = models.Group.query(user.key == models.Group.invited_members)
        if 'assignment' in data:
            assignment = models.Assignment.get_by_id(data['assignment'])
            if assignment:
                query = query.filter(models.Group.assignment == assignment.key)
            else:
                return {
                    "invitations": []
                }
        return {
            "invitations": [{
                "members": invitation.members,
                "id": invitation.key.id(),
                "assignment": invitation.assignment,
            } for invitation in list(query)]
        }

    def accept_invitation(self, user, obj):
        data = self.parse_args(False, user)
        if 'invitation' not in data:
            return
        group = models.Group.get_by_id(data['invitation'])
        if group:
            assignment = group.assignment.get()
            if len(group.members) < assignment.max_group_size:
                already_in_group = len(list(user.get_groups(assignment))) > 0
                if not already_in_group:
                    if user.key in group.invited_members:
                        group.invited_members.remove(user.key)
                        group.members.append(user.key)
                    group.put()

    def reject_invitation(self, user, obj):
        data = self.parse_args(False, user)
        if 'invitation' not in data:
            return
        group = models.Group.get_by_id(data['invitation'])
        if group:
            if user.key in group.invited_members:
                group.invited_members.remove(user.key)
                group.put()



class AssignmentAPI(APIResource):
    """The API resource for the Assignment Object"""
    model = models.Assignment

    web_args = {
        'name': Arg(str),
        'points': Arg(float),
        'course': KeyArg('Course'),
        'max_group_size': Arg(int),
        'templates': Arg(str, use=lambda temps: json.dumps(temps)),
    }

    def parse_args(self, is_index, user):
        data = super(AssignmentAPI, self).parse_args(is_index, user)
        if not is_index:
            data['creator'] = user.key
        return data

    def group(self, obj, user):
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

    def download(self, obj, user):
        """
        Allows you to download a submission.
        """
        if 'file_contents' not in obj.messages:
            return 400, "Submission has no contents to download."

        response = make_response(create_zip(obj.messages['file_contents']))
        response.headers["Content-Disposition"] = (
            "attachment; filename=submission-%s.zip" % str(obj.created))
        response.headers["Content-Type"] = "application/zip"
        return response

    def diff(self, obj, user):
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

    def add_comment(self, obj, user):
        """
        Adds a comment to this diff.
        """
        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if not diff_obj:
            raise BadValueError("Diff doesn't exist yet")

        data = self.parse_args(False, user)
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

    def delete_comment(self, obj, user):
        """
        Deletes a comment on this diff.
        """
        diff_obj = self.diff_model.get_by_id(obj.key.id())
        if not diff_obj:
            raise BadValueError("Diff doesn't exist yet")

        data = self.parse_args(False, user)
        comment = data.get('comment', None)
        if not comment:
            return 400, "Missing required argument 'comment'"

        comment = models.Comment.get_by_id(comment)
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

    def post(self, user):
        data = self.parse_args(False, user)
        if 'assignment' not in data:
            raise BadValueError("Missing required arguments 'assignment'")
        if 'messages' not in data:
            raise BadValueError("Missing required arguments 'messages'")

        return self.submit(user, data['assignment'],
                           data['messages'])

    web_args = {
        'assignment': Arg(str),
        'messages': Arg(None),
        'message': Arg(str),
        'file': Arg(str),
        'index': Arg(int),
        'comment': Arg(int),
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

    def parse_args(self, is_index, user):
        data = super(CourseAPI, self).parse_args(is_index, user)
        if not is_index:
            data['creator'] = user.key
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

    def add_member(self, obj, user):
        data = self.parse_args(False, user)

        for member in data['members']:
            if member not in obj.invited_members:
                member = models.User.get_or_insert(member.id())
                obj.invited_members.append(member.key)
                break
        else:
            return

        #TODO(martinis) make this async
        obj.put()

        audit_log_message = models.AuditLog(
            event_type='Group.add_member',
            user=user.key,
            description="Added members {} to group".format(data['members']),
            obj=obj.key
            )
        audit_log_message.put()

    def remove_member(self, obj, user):
        data = self.parse_args(False, user)

        changed = False
        for member in data['members']:
            if member in obj.members:
                changed = True
                obj.members.remove(member)
            if member in obj.invited_members:
                changed = True
                obj.invited_members.remove(member)

        if not changed:
            return 400, "Tried to remove a user which is not part of this group"

        audit_log_message = models.AuditLog(
            event_type='Group.remove_member',
            user=user.key,
            obj=obj.key
            )

        message = ""
        if len(obj.members) == 0:
            obj.key.delete()
            message = "Deleted group"
        else:
            obj.put()
            message = "Removed members {} from group".format(data['members'])

        audit_log_message.description = message
        audit_log_message.put()

    def put(self, *args):
        return 404, "No PUT allowed"

    def post(self, *args):
        return 404, "No POST allowed"
