"""Data Models."""

#pylint: disable=no-member
#pylint: disable=unused-argument
#pylint: disable=too-many-return-statements

import datetime

from app import app
from app.constants import STUDENT_ROLE, STAFF_ROLE, VALID_ROLES
from app.exceptions import *
from flask import json
from flask.json import JSONEncoder as old_json

from google.appengine.ext import ndb

class JSONEncoder(old_json):
    """
    Wrapper class to try calling an object's to_dict() method. This allows
    us to JSONify objects coming from the ORM. Also handles dates & datetimes.
    """
    def default(self, obj):
        if isinstance(obj, ndb.Key):
            got = obj.get()
            if not got:
                return None
            return got.to_json()
        elif isinstance(obj, datetime.datetime):
            obj = convert_timezone(obj)
            return obj.strftime(app.config["GAE_DATETIME_FORMAT"])
        if isinstance(obj, ndb.Model):
            return obj.to_json()
        return super(JSONEncoder, self).default(obj)

app.json_encoder = JSONEncoder

def convert_timezone(utc_dt):
    """Convert times to Pacific time."""
    # This looks like a hack... is it even right? What about daylight savings?
    # Correct approach: each course should have a timezone. All times should be
    # stored in UTC for easy comparison. Dates should be converted to
    # course-local time when displayed.
    delta = datetime.timedelta(hours=-7)
    return datetime.datetime.combine(utc_dt.date(), utc_dt.time()) + delta


class Base(ndb.Model):
    """Shared utility methods and properties."""
    created = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        inst = cls()
        inst.populate(**values)
        return inst

    def to_json(self, fields=None):
        """Converts this model to a json dictionary."""
        if fields == True:
            return self.to_dict()
        elif fields == False:
            return {}

        if not fields:
            fields = {}
        if fields:
            result = self.to_dict(include=fields.keys())
        else:
            result = self.to_dict()

        if self.key and (not fields or 'id' in fields):
            result['id'] = self.key.id()

        for key, value in result.items():
            if isinstance(value, ndb.Key):
                value = value.get()
                if value:
                    result[key] = value.to_json(fields.get(key))
                else:
                    result[key] = None
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], ndb.Key):
                new_list = []
                for value in value:
                    fields_key = fields.get(key)
                    if fields_key and not isinstance(fields_key, dict):
                        if fields.get(key):
                            new_list.append(value)
                    else:
                        value = value.get()
                        if value:
                            new_list.append(value.to_json(fields.get(key)))
                result[key] = new_list
            else:
                try:
                    new_value = app.json_encoder().default(value)
                    result[key] = new_value
                except TypeError:
                    pass
        return result

    @classmethod
    def can(cls, user, need, obj=None, query=None):
        """Whether user satisfies the given need for this object.

        The index action requires a query that gets filtered and returned.
        """
        if need.action == "index":
            assert query, "No query for index"
        need.set_object(obj or cls)
        return cls._can(user, need, obj, query)

    @classmethod
    def _can(cls, user, need, obj, query):
        """
        The internal permissions method. Overridden by subclasses.
        """
        return False


class User(Base):
    """Users may have multiple email addresses. Note: the built-in user model
    in appengine associates a different user object with each email.
    """
    email = ndb.StringProperty(repeated=True)
    is_admin = ndb.BooleanProperty(default=False)
    # TODO add a name
    # TODO add a student ID

    @property
    def logged_in(self):
        return self.email != ["_anon"]

    def append_email(self, email):
        if email not in self.email:
            self.email.append(email)

    def delete_email(self, email):
        if email in self.email and len(self.email) > 1:
            self.email.remove(email)

    def get_final_submission(self, assignment):
        query = Group.query(Group.member == self.key)
        group = query.filter(Group.assignment == assignment)
        return FinalSubmission.query(FinalSubmission.group == group)

    def get_backups(self, assignment):
        query = Group.query(Group.member == self.key)
        group = query.filter(Group.assignment == assignment)
        all_backups = []

        for member in group.member:
            all_backups += list(Backup.query(
                Backup.submitter == member).filter(
                    Backup.assignment == assignment))

        return all_backups

    def get_submissions(self, assignment):
        all_submissions = []

        for backup in self.get_backups(assignment):
            if len(Submission.query(Submission.backup == backup.key)) > 0:
                all_submissions.append(backup)

        return all_submissions


    def get_group(self, assignment):
        query = Group.query(Group.member == self.key)
        group = query.filter(Group.assignment == assignment)
        return group.get()

    def get_course_info(self, course):
        info = {'user': self}
        info['assignments'] = []

        for assignment in course.assignments():
            assign_info['group'] = self.get_group(assignment)
            assign_info['final'] = self.get_final_submission(assignment)
            assign_info['backups'] = self.get_backups(assignment)
            assign_info['assignment'] = assignment
            info['assignments'].append(assign_info)

        return info

    #@ndb.transactional
    @classmethod
    def get_or_insert(cls, email):
        """Retrieve a user by email or create that user."""
        user = cls.lookup(email)
        if user:
            return user
        else:
            user = cls(email=[email])
            user.put()
            return user

    @classmethod
    def lookup(cls, email):
        """Retrieve a user by email or return None."""
        assert isinstance(email, str), "Invalid email: " + str(email)
        return cls.query(cls.email == email).get()

    @classmethod
    def _can(cls, user, need, obj, query):
        if not user.logged_in:
            return False
        if user.is_admin:
            return True

        if need.action == "lookup":
            return True
        if need.action == "get":
            if not obj or not isinstance(obj, User):
                return False
            elif obj.key == user.key:
                return True
            else:
                for part in Participant.courses(user, STAFF_ROLE):
                    course = part.course
                    if Participant.has_role(obj, course, STUDENT_ROLE):
                        return True
                return False
        elif need.action == "index":
            # TODO Update documentation: users can only index themselves.
            #      See Participant for listing users by course
            return query.filter(User.key == user.key)
        else:
            return False

    def _pre_put_hook(self):
        """Ensure that a user can be accessed by at least one email."""
        if not self.email:
            raise BadValueError("No email associated with " + str(self))

class Course(Base):
    """Courses are expected to have a unique offering."""
    offering = ndb.StringProperty() # E.g., 'cal/cs61a/fa14'
    institution = ndb.StringProperty() # E.g., 'UC Berkeley'
    display_name = ndb.StringProperty()
    instructor = ndb.KeyProperty(User, repeated=True)
    active = ndb.BooleanProperty(default=True)

    @property
    def staff(self):
        """
        Returns all the staff of this course.
        """
        return [part.user for part in Participant.query(
            Participant.course == self.key,
            Participant.role == STAFF_ROLE).fetch()]

    @classmethod
    def _can(cls, user, need, course, query):
        action = need.action
        if action == "get":
            return True
        elif action == "index":
            return query
        elif action == "modify":
            return bool(course) and user.key in course.staff
        elif action == "staff":
            if user.is_admin:
                return True
            return user.key in course.staff
        elif action == "create":
            return user.is_admin
        return False

    @property
    def assignments(self):
        """Return a query for assignments."""
        return Assignment.query(Assignment.course == self.key)


class Assignment(Base):
    """Assignments are particular to courses and have unique names."""
    name = ndb.StringProperty() # E.g., cal/cs61a/fa14/proj1
    display_name = ndb.StringProperty()
    points = ndb.FloatProperty()
    templates = ndb.JsonProperty()
    creator = ndb.KeyProperty(User)
    course = ndb.KeyProperty(Course)
    max_group_size = ndb.IntegerProperty()
    due_date = ndb.DateTimeProperty()
    lock_date = ndb.DateTimeProperty() # no submissions after this date
    active = ndb.ComputedProperty(
        lambda a: a.lock_date and datetime.datetime.now() <= a.lock_date)
    # TODO Add services requested

    @classmethod
    def _can(cls, user, need, obj, query):
        if need.action == "get":
            return True
        elif need.action == "index":
            return query
        elif need.action == "create":
            if obj and isinstance(obj, Assignment):
                return Participant.has_role(user, obj.course, STAFF_ROLE)
        elif need.action == "grade":
            if obj and isinstance(obj, Assignment):
                return Participant.has_role(user, obj.course, STAFF_ROLE)
        return False


class Participant(Base):
    """Tracks participation of students & staff in courses."""
    user = ndb.KeyProperty(User)
    course = ndb.KeyProperty(Course)
    role = ndb.StringProperty() # See constants.py for roles

    @classmethod
    def _can(cls, user, need, course, query):
        action = need.action
        if action == "get":
            return True
        elif action == "index":
            if cls.has_role(user, self.course, STAFF_ROLE):
                return query.filter(cls.course == course)
            else:
                return query.filter(cls.user == user)

    @classmethod
    def add_role(cls, user_key, course_key, role):
        if role not in VALID_ROLES:
            raise BadValueError("Bad role: " + str(role))
        if isinstance(user_key, User):
            user_key = user_key.key
        if isinstance(course_key, Course):
            course_key = course_key.key
        Participant(user=user_key, course=course_key, role=role).put()

    @classmethod
    def has_role(cls, user_key, course_key, role):
        if isinstance(user_key, User):
            user_key = user_key.key
        if isinstance(course_key, Course):
            course_key = course_key.key
        query = cls.query(cls.user == user_key,
                          cls.course == course_key,
                          cls.role == role)
        return query.get() is not None

    @classmethod
    def courses(cls, user_key, role=None):
        if isinstance(user_key, User):
            user_key = user_key.key
        query = cls.query(cls.user == user_key)
        if role:
            query = query.filter(cls.role == role)
        return query.fetch()


def validate_messages(_, message_str):
    """message_str is a JSON string encoding a map from protocols to data."""
    if not message_str:
        raise BadValueError('Empty messages')
    try:
        messages = json.loads(message_str)
        if not isinstance(messages, dict):
            raise BadValueError('messages is not a JSON map')
    except Exception as exc:
        raise BadValueError(exc)


class Message(Base):
    """A message given to us from the client (e.g., the contents of files)."""
    contents = ndb.JsonProperty()
    kind = ndb.StringProperty()

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action

        if action == "index":
            return False

        return Backup._can(user, need, obj, query)


def disjunction(query, filters):
    """Return a query in which at least one filter is true."""
    assert filters, "No filters"
    if len(filters) > 1:
        return query.filter(ndb.OR(*filters)) #pylint: disable=star-args
    else:
        return query.filter(filters[0])


class Backup(Base):
    """A backup is sent each time a student runs the client."""
    submitter = ndb.KeyProperty(User)
    assignment = ndb.KeyProperty(Assignment)
    client_time = ndb.DateTimeProperty()
    messages = ndb.StructuredProperty(Message, repeated=True)
    tags = ndb.StringProperty(repeated=True)

    def get_messages(self, fields=None):
        """Returns self.messages formatted as a dictionary.

        fields: The selected fields of the dictionary.
        """

        if not fields:
            fields = {}

        # TODO What does this do and why? Please add a comment.
        message_fields = fields.get('messages', {})
        if isinstance(message_fields, (str, unicode)):
            message_fields = message_fields == "true"

        messages = {m.kind: m.contents for m in self.messages}
        def test(item):
            if isinstance(message_fields, bool):
                return message_fields

            if not message_fields:
                return True
            return item in message_fields

        def get_contents(kind, contents):
            if isinstance(message_fields, bool):
                return contents

            if message_fields.get(kind) == "presence":
                return True
            return contents

        return {
            kind: get_contents(kind, contents)
            for kind, contents in messages.iteritems()
            if test(kind)}

    @property
    def group(self):
        return Group.lookup(self.submitter, self.assignment)

    def to_json(self, fields=None):
        json = super(Backup, self).to_json(fields)
        if 'messages' in json:
            json['messages'] = self.get_messages(fields)
        return json

    @classmethod
    def _can(cls, user, need, backup, query):
        """A user can access a backup as staff or through a group."""
        action = need.action
        if action == "get":
            if not backup or not isinstance(backup, Backup):
                raise ValueError("Need Backup instance for get action.")
            if user.is_admin or backup.submitter == user.key:
                return True
            course_key = backup.assignment.get().course
            if Participant.has_role(user, course_key, STAFF_ROLE):
                return True
            group = backup.group
            return bool(group and user.key in group.member)
        if action in ("create", "put"):
            return user.logged_in and user.key == backup.submitter
        if action == "index":
            if not user.logged_in:
                return False
            filters = [Backup.submitter == user.key]
            staff_list = Participant.courses(user, STAFF_ROLE)
            if user.key in [part.user for part in staff_list]:
                for participant in staff_list:
                    course = participant.course
                    assigns = Assignment.query(Assignment.course == course).fetch()
                    if assigns:
                        filters.append(
                            Backup.assignment.IN([a.key for a in assigns]))
            grp = backup and backup.group
            if grp and user.key in grp.member:
                filters.append(ndb.AND(
                    Backup.submitter.IN(grp.member),
                    Backup.assignment == grp.assignment))
            return disjunction(query, filters)
        return False


class Score(Base):
    """The score for a submission, either from a grader or autograder."""
    score = ndb.IntegerProperty()
    message = ndb.StringProperty() # Plain text
    grader = ndb.KeyProperty('User')
    autograder = ndb.StringProperty()


class Submission(Base):
    """A backup that may be scored."""
    backup = ndb.KeyProperty(Backup)
    score = ndb.StructuredProperty(Score, repeated=True)

    @classmethod
    def _can(cls, user, need, submission, query):
        return Backup._can(user, need, submission.backup.get(), query)


class Diff(Base):
    """A diff between two versions of the same project, with comments.
    A diff has three types of lines: insertions, deletions, and matches.
    Every insertion line is associated with a diff line.
    """
    before = ndb.KeyProperty(Backup) # Set to None to compare to template
    after = ndb.KeyProperty(Backup)
    diff = ndb.JsonProperty()

    @property
    def comments(self):
        """
        Returns all the comments for this diff.
        """
        return Comment.query(ancestor=self.key).order(Comment.created)

    def to_json(self, fields=None):
        data = super(Diff, self).to_json(fields)
        comments = list(self.comments)
        all_comments = {}
        for comment in comments:
            file_comments = all_comments.set_default(comment.filename, {})
            file_comments.set_default(comment.line, []).append(comment)

        data['comments'] = all_comments
        return data


class Comment(Base):
    """A comment is part of a diff. The key has the diff as its parent."""
    author = ndb.KeyProperty('User')
    diff = ndb.KeyProperty('Diff')
    filename = ndb.StringProperty()
    line = ndb.IntegerProperty()
    # TODO Populate submission_line so that when diffs are changed, comments
    #      don't move around.
    submission_line = ndb.IntegerProperty()
    message = ndb.TextProperty() # Markdown

    @classmethod
    def _can(cls, user, need, comment=None, query=None):
        if need.action in ["get", "modify", "delete"]:
            return comment.author == user.key
        return False


class Version(Base):
    """A version of client-side resources. Used for auto-updating."""
    name = ndb.StringProperty(required=True)
    versions = ndb.StringProperty(repeated=True)
    current_version = ndb.StringProperty()
    base_url = ndb.StringProperty(required=True)

    def download_link(self, version=None):
        if version is None:
            if not self.current_version:
                raise BadValueError("current version doesn't exist")
            return '/'.join((self.base_url, self.current_version,
                             self.name))
        if version not in self.versions:
            raise BadValueError("specified version %s doesn't exist" % version)
        return '/'.join((self.base_url, version, self.name))

    def to_json(self, fields=None):
        converted = super(Version, self).to_json(fields)
        if self.current_version:
            converted['current_download_link'] = self.download_link()

        return converted

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action

        if action == "delete":
            return False
        if action == "index":
            return query
        if action == "get":
            return True
        return user.is_admin

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        if 'name' not in values:
            raise ValueError("Need to specify a name")
        inst = cls(key=ndb.Key('Version', values['name']))
        inst.populate(**values) #pylint: disable=star-args
        return inst

    @classmethod
    def get_or_insert(cls, key, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for versions"
        kwargs['name'] = key
        return super(cls, Version).get_or_insert(key, **kwargs)

    @classmethod
    def get_by_id(cls, key, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for versions"
        return super(cls, Version).get_by_id(key, **kwargs)

class Group(Base):
    """A group is a collection of users who are either members or invited.

    Members of a group can view each other's submissions.
    """
    member = ndb.KeyProperty(kind='User', repeated=True)
    invited = ndb.KeyProperty(kind='User', repeated=True)
    assignment = ndb.KeyProperty('Assignment', required=True)

    @classmethod
    def lookup(cls, user_key, assignment_key):
        """Return the group for a user key."""
        if isinstance(user_key, User):
            user_key = user_key.key()
        if isinstance(assignment_key, Assignment):
            assignment_key = assignment_key.key()
        return Group.query(Group.member == user_key,
                           Group.assignment == assignment_key).get()

    @classmethod
    def _lookup_or_create(cls, user_key, assignment_key):
        """Retrieve a group for user or create a group. Group is *not* put."""
        group = cls.lookup(user_key, assignment_key)
        if group:
            return group
        if isinstance(user_key, User):
            user_key = user_key.key()
        if isinstance(assignment_key, Assignment):
            assignment_key = assignment_key.key()
        return Group(member=[user_key], invited=[], assignment=assignment_key)

    #@ndb.transactional
    def invite(self, email):
        """Invites a user to the group. Returns an error message or None."""
        user = User.lookup(email)
        if not user:
            return "That user does not exist"
        course = self.assignment.get().course
        if not Participant.has_role(user, course, STUDENT_ROLE):
            return "That user is not enrolled in this course"
        if user.key in self.member or user.key in self.invited:
            return "That user is already in the group"
        has_user = ndb.OR(Group.member == user.key, Group.invited == user.key)
        if Group.query(has_user, Group.assignment == self.assignment).get():
            return "That user is already in some other group"
        max_group_size = self.assignment.get().max_group_size
        total_member = len(self.member) + len(self.invited)
        if total_member + 1 > max_group_size:
            return "The group is full"
        self.invited.append(user.key)
        self.put()

    #@ndb.transactional
    @classmethod
    def invite_to_group(cls, user_key, email, assignment_key):
        """User invites email to join his/her group. Returns error or None."""
        group = cls._lookup_or_create(user_key, assignment_key)
        return group.invite(email)

    #@ndb.transactional
    def accept(self, user_key):
        """User accepts an invitation to join. Returns error or None."""
        if user_key not in self.invited:
            return "That user is not invited to the group"
        if user_key in self.member:
            return "That user has already accepted."
        self.invited.remove(user_key)
        self.member.append(user_key)
        self.put()

    #@ndb.transactional
    def exit(self, user_key):
        """User leaves the group. Empty/singleton groups are deleted."""
        for users in [self.member, self.invited]:
            if user_key in users:
                users.remove(user_key)
        if not self.validate():
            self.key.delete()

    @classmethod
    def _can(cls, user, need, group, query):
        action = need.action
        if not user.logged_in:
            return False

        if action == "index":
            if user.is_admin:
                return query
            return query.filter(ndb.OR(Group.member == user.key,
                                       Group.invited == user.key))

        if user.is_admin:
            return True
        if not group:
            return False
        if action in ("get", "exit"):
            return user.key in group.member or user.key in group.invited
        elif action in ("invite", "rescind"):
            return user.key in group.member
        elif action == "accept":
            return user.key in group.invited
        return False

    def validate(self):
        """Return an error string if group is invalid."""
        max_group_size = self.assignment.get().max_group_size
        total_member = len(self.member) + len(self.invited)
        if max_group_size and total_member > max_group_size:
            sizes = (total_member, max_group_size)
            return "%s member found; at most %s allowed" % sizes
        if total_member < 2:
            return "No group can have %s total member" % total_member
        if not self.member:
            return "A group must have an active member"

    def _pre_put_hook(self):
        """Ensure that the group is well-formed before put."""
        error = self.validate()
        if error:
            raise BadValueError(error)


def anon_converter(prop, value):
    """Convert anonymous user to None."""
    if not value.get().logged_in:
        return None
    return value


class AuditLog(Base):
    """Keeps track of Group changes that are happening. That way, we can stop
    cases of cheating by temporary access. (e.g. A is C's partner for 10 min
    so A can copy off of C)."""
    event_type = ndb.StringProperty(required=True)
    user = ndb.KeyProperty('User', required=True, validator=anon_converter)
    description = ndb.StringProperty()
    obj = ndb.KeyProperty()


class Queue(Base):
    """A queue of submissions to grade."""
    assignment = ndb.KeyProperty(Assignment)
    assigned_staff = ndb.KeyProperty(User, repeated=True)

    @property
    def submissions(self):
        """
        Returns all the submissions in this queue.
        """
        query = FinalSubmission.query().filter(FinalSubmission.queue == self.key)
        return [fs.submission for fs in query]

    def to_json(self, fields=None):
        if not fields:
            fields = {}

        return {
            'submissions': [{'id': val.id()} for val in self.submissions],
            'assignment': self.assignment.get(),
            'assigned_staff': [val.get().to_json(fields.get('assigned_staff')) for val in self.assigned_staff],
            'id': self.key.id()
        }


class FinalSubmission(Base):
    """The final submission for an assignment from a group."""
    assignment = ndb.KeyProperty(Assignment)
    group = ndb.KeyProperty(Group)
    submission = ndb.KeyProperty(Submission)
    published = ndb.BooleanProperty(default=False)
    queue = ndb.KeyProperty(Queue)

    @property
    def assigned(self):
        """
        Return whether or not this assignment has been assigned to a queue.
        """
        return bool(self.queue)

    @classmethod
    def _can(cls, user, need, final, query):
        return Submission._can(user, need, final.submission.get(), query)

    # TODO Add hook to update final submissions on submission or group change.





