"""

DATA MODELS

This file is responsible for models and business logic. In 
here, all methods should handle:

    - permission checks
      Check user for each operation.
      
    - basic operations
      Get, put, delete. All of those go in here.
      
    - queries
      Search queries all go in here.

Methods in here should try to throw informational BadValueErrors
upon failure.

Parsing web arguments and error handling go in api.py.
      
Specification: https://github.com/Cal-CS-61A-Staff/ok/wiki/Models
"""

#pylint: disable=no-member, unused-argument, too-many-return-statements

import datetime
import itertools

from app import app
from app.constants import STUDENT_ROLE, STAFF_ROLE, VALID_ROLES
from app.exceptions import *
from app import utils
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

    @classmethod
    def _get_kind(cls):
        return cls.__name__ + 'v2'

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

def make_num_counter(helper):
    def wrapper(self, assignment, max_size=None):
        count = 0

        all_submissions = helper(self, assignment)
        if max_size is not None:
            left_to_count = max_size
            for submission_query in all_submissions:
                if count >= max_size:
                    break
                diff = submission_query.count(left_to_count)
                left_to_count -= diff
                count += diff
        else:
            for submission_query in all_submissions:
                count += submission_query.count(max_size)


        return count
    return wrapper

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

    def get_final_submission(self, assignment_key):
        """Get the current final submission for this user."""
        if isinstance(assignment_key, Assignment):
            assignment_key = assignment_key.key
        group = self.get_group(assignment_key)
        if group and self.key in group.member:
            return FinalSubmission.query(
                FinalSubmission.assignment==assignment_key,
                FinalSubmission.group==group.key).get()
        else:
            return FinalSubmission.query(
                FinalSubmission.assignment==assignment_key,
                FinalSubmission.submitter==self.key).get()

    def _contains_files(self, backup):
        messages = backup.get_messages()
        if 'file_contents' in messages:
            return messages['file_contents']

    def _get_backups_helper(self, assignment):
        group = self.get_group(assignment)
        if not group or self.key not in group.member:
            members = [self.key]
        else:
            members = group.member

        all_backups = []
        for member in members:
            all_backups.append(Backup.query(
                Backup.submitter == member,
                Backup.assignment == assignment))

        return all_backups

    def get_backups(self, assignment, num_backups=10):
        queries = self._get_backups_helper(assignment)
        backups = [query.fetch(num_backups) for query in queries]
        all_backups = []
        for results in backups:
            for b in results:
                all_backups.append(b)

        all_backups.sort(lambda x, y: int(-5*(int(x.server_time > y.server_time) - 0.5)))

        return all_backups[:num_backups]

    def _get_submissions_helper(self, assignment):
        group = self.get_group(assignment)
        if not group or self.key not in group.member:
            members = [self.key]
        else:
            members = group.member

        all_submissions = []
        for member in members:
            all_submissions.append(Submission.query(
                Submission.submitter==member,
                Submission.assignment==assignment))

        return all_submissions

    def get_submissions(self, assignment, num_submissions=10):
        queries = self._get_submissions_helper(assignment)

        subms = [query.fetch() for query in queries]
        all_subms = []
        for results in subms:
            for s in results:
                all_subms.append(s)

        def update(x):
            b = x.backup.get()
            b.submission = x
            return b
        
        all_subms = [update(x) for x in all_subms]
        all_subms = [x for x in all_subms if x.assignment == assignment \
                and self._contains_files(x)]

        all_subms.sort(lambda x, y: int(-5*(int(x.server_time > y.server_time) - 0.5)))
        
        return all_subms[:num_submissions]

    get_num_submissions = make_num_counter(_get_submissions_helper)
    get_num_backups = make_num_counter(_get_backups_helper)


    def get_group(self, assignment_key):
        """Return the group for this user for an assignment."""
        if isinstance(assignment_key, Assignment):
            assignment_key = assignment_key.key
        return Group.query(ndb.OR(Group.member==self.key,
                                  Group.invited==self.key),
                           Group.assignment==assignment_key).get()

    def get_course_info(self, course):
        if not course:
            raise BadValueError("Invalid course")

        info = {'user': self}
        info['assignments'] = []
        assignments = sorted(course.assignments)

        for assignment in assignments:
            assign_info = {}
            group = self.get_group(assignment.key)
            assign_info['group'] = {'group_info': group, 'invited': group and self.key in group.invited}
            assign_info['final'] = {}
            final_info = assign_info['final']

            final_info['final_submission'] = self.get_final_submission(assignment.key)
            if final_info['final_submission']:
                final_info['submission'] = final_info['final_submission'].submission.get()
                final_info['backup'] = final_info['submission'].backup.get()

                if final_info['final_submission'].revision:
                    final_info['revision'] = final_info['final_submission'].revision.get()

                final_info['backup'] = final_info['submission'].backup.get()

                # Percentage
                final = final_info['backup']
                solved = 0
                total = 0
                for message in final.messages:
                    if message.kind == 'grading':
                        for test_type in message.contents:
                            for key in message.contents[test_type]:
                                value = message.contents[test_type][key]
                                if key == 'passed':
                                    solved += value
                                if type(value) == int:
                                    total += value
                if total > 0:
                    assign_info['percent'] = round(100*float(solved)/total, 0)

            assign_info['backups'] = self.get_num_backups(assignment.key, 1) > 0
            assign_info['submissions'] = self.get_num_submissions(assignment.key, 1) > 0
            assign_info['assignment'] = assignment

            info['assignments'].append(assign_info)

        return info

    def update_final_submission(self, assignment, group=None):
        """Update the final submission of the user and its group.
        Call on all users after group changes.
        """
        if isinstance(assignment, Assignment):
            assignment = assignment.key

        options = [FinalSubmission.submitter == self.key]
        if not group:
            group = self.get_group(assignment)
        if group and self.key in group.member:
            options.append(FinalSubmission.group == group.key)
            options += [FinalSubmission.submitter == m for m in group.member]
        who = options[0] if len(options) == 1 else ndb.OR(*options)
        assigned = FinalSubmission.assignment == assignment
        finals = FinalSubmission.query(assigned, who).fetch()

        if finals:
            # Keep the most recent and delete the rest.
            # Note: Deleting a FinalSubmission does not delete its submission.
            finals.sort(key=lambda final: final.submission.get().server_time)
            old, latest = finals[:-1], finals[-1]
            latest.group = group.key if group else None
            latest.put()
            for final in old:
                final.key.delete()
        else:
            # Create a final submission for user from her latest submission.
            subs = Submission.query(
                Submission.submitter == self.key,
                Submission.assignment == assignment)
            latest = subs.order(-Submission.server_time).get()
            if latest:
                FinalSubmission(assignment=assignment,
                                group=group.key if group else None,
                                submission=latest.key).put()

    #@ndb.transactional
    @classmethod
    def get_or_insert(cls, email):
        """Retrieve a user by email or create that user."""
        email = email.lower()
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
        assert isinstance(email, (str, unicode)), "Invalid email: " + str(email)
        email = email.lower()
        users = cls.query(cls.email == email).fetch()
        if not users:
            return None
        if len(users) > 1:
            pass # TODO Decide how to handle non-unique users
        return users[0]

    @classmethod
    def _can(cls, user, need, obj, query):
        if not user.logged_in:
            return False
        if user.is_admin:
            if need.action == "index":
                return query
            return True

        if need.action == "lookup":
            return True
        elif need.action == "merge":
            # TODO(soumya) figure out how to make permissions for this
            return False
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
        #utils.check_user(self.key.id())

    def scores_for_assignment(self, assignment):
        """ Returns a tuple of two elements: 
                1) Score data (list of lists) for STUDENT's final submission for ASSIGNMENT.
                    There is an element for each score. 
                    * OBS * If the student is in a group, the list will contain an
                    element for each combination of group member and score.
                2) A boolean indicating whether the student had a
                    scored final submission for ASSIGNMENT. 
            Format: [['STUDENT', 'SCORE', 'MESSAGE', 'GRADER', 'TAG']]
        """
        fs = self.get_final_submission(assignment.key)
        scores = []
        if fs:
            scores = fs.get_scores()
        return (scores, True) if scores else ([[self.email[0], 0, None, None, None]], False)

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

    def get_students(self, user):

        query = Participant.query(
            Participant.course == self.key,
            Participant.role == 'student')

        return list(query.fetch())


class Assignment(Base):
    """Assignments are particular to courses and have unique names."""
    name = ndb.StringProperty() # E.g., cal/cs61a/fa14/proj1
    display_name = ndb.StringProperty()
    url = ndb.StringProperty()
    points = ndb.FloatProperty()
    templates = ndb.JsonProperty()
    creator = ndb.KeyProperty(User)
    course = ndb.KeyProperty(Course)
    max_group_size = ndb.IntegerProperty()
    due_date = ndb.DateTimeProperty()
    lock_date = ndb.DateTimeProperty() # no submissions after this date
    active = ndb.ComputedProperty(
        lambda a: a.due_date and datetime.datetime.now() <= a.due_date)
    revision = ndb.BooleanProperty(default=False)
    autograding_enabled = ndb.BooleanProperty(default=False)
    grading_script_file = ndb.TextProperty()
    zip_file_url = ndb.StringProperty()

    # TODO Add services requested

    @classmethod
    def _can(cls, user, need, obj, query):
        if need.action == "index":
            return query
        if user.is_admin:
            return True
        if need.action == "get":
            return True
        elif need.action in ["grade", 'delete', 'create', 'put']:
            if obj and isinstance(obj, Assignment):
                return Participant.has_role(user, obj.course, STAFF_ROLE)
        return False

    def __lt__(self, other):
        """ Allows us to sort assignments - reverse order so that latest due dates come first """
        return self.due_date > other.due_date


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
        elif action == "staff":
            if user.is_admin:
                return True
            return user.key in course.staff
        elif action == "index":
            if cls.has_role(user, course, STAFF_ROLE):
                return query.filter(cls.course == course.key)
            else:
                return query.filter(cls.user == user.key)

    @classmethod
    def add_role(cls, user_key, course_key, role):
        if role not in VALID_ROLES:
            raise BadValueError("Bad role: " + str(role))
        if isinstance(user_key, User):
            user_key = user_key.key
        if isinstance(course_key, Course):
            course_key = course_key.key

        query = cls.query(cls.user == user_key,
                          cls.course == course_key,
                          cls.role == role)
        current = query.get()
        if not current:
            Participant(user=user_key, course=course_key, role=role).put()

    @classmethod
    def remove_role(cls, user_key, course_key, role):
        if role not in VALID_ROLES:
            raise BadValueError("Bad role: " + str(role))
        if isinstance(user_key, User):
            user_key = user_key.key
        if isinstance(course_key, Course):
            course_key = course_key.key
        query = cls.query(cls.user == user_key,
                          cls.course == course_key,
                          cls.role == role)
        current = query.get()
        if current:
            current.key.delete()

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
    server_time = ndb.DateTimeProperty(auto_now_add=True)
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
        if action == "staff":
            if user.is_admin:
                return True
            course_key = backup.assignment.get().course
            course = course_key.get()
            return user.key in course.staff
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
    tag = ndb.TextProperty() # E.g., "Partner 0" or "composition"
    score = ndb.IntegerProperty()
    message = ndb.TextProperty() # Plain text
    grader = ndb.KeyProperty(User) # For autograders, the user who authenticated
    server_time = ndb.DateTimeProperty(auto_now_add=True)


class Submission(Base):
    """A backup that may be scored."""
    backup = ndb.KeyProperty(Backup)
    score = ndb.StructuredProperty(Score, repeated=True)
    submitter = ndb.ComputedProperty(lambda x: x.backup.get().submitter)
    assignment = ndb.ComputedProperty(lambda x: x.backup.get().assignment)
    server_time = ndb.DateTimeProperty(auto_now_add=True)
    is_revision = ndb.BooleanProperty(default=False)

    def get_final(self):
        assignment = self.assignment
        # I have no idea why this works... need it to pass tests
        group = self.submitter.get().get_group(assignment)
        submitter = self.submitter
        if group:
            final = FinalSubmission.query(
                FinalSubmission.assignment==assignment,
                FinalSubmission.group==group.key).get()
        else:
            final = FinalSubmission.query(
                FinalSubmission.assignment==assignment,
                FinalSubmission.submitter==submitter).get()
        return final

    def mark_as_final(self):
        """Create or update a final submission."""
        final = self.get_final()
        if final:
            assignment = self.assignment.get()
            if assignment.revision:
                # Follow resubmssion procedure
                final.revision = self.key
            else:
                final.submitter = self.submitter
                final.submission = self.key
        else:
            group = self.submitter.get().get_group(self.assignment)
            final = FinalSubmission(
                assignment=self.assignment, submission=self.key)
            if group:
                final.group = group.key
        return final.put()

    def resubmit(self, user_key):
        """
        Resubmits this submission as being submitted by |user|.
        """
        old_backup = self.backup.get()
        new_backup = Backup(
            submitter=user_key,
            assignment=self.assignment,
            client_time=old_backup.client_time,
            server_time=old_backup.server_time,
            messages=old_backup.messages,
            tags=old_backup.tags)
        new_backup_key = new_backup.put()
        new_subm = Submission(
            backup=new_backup_key,
            score=self.score,
            server_time=self.server_time)
        new_subm_key = new_subm.put_async()

        final = self.get_final()
        if final:
            final.submitter = user_key
            final.submission = new_subm_key.get_result()
            final.put()

    @classmethod
    def _can(cls, user, need, submission, query):
        if need.action == "grade":
            if not submission or not isinstance(submission, Submission):
                raise ValueError("Need Submission instance for grade action")
            if user.is_admin:
                return True
            course_key = submission.assignment.get().course
            return Participant.has_role(user, course_key, STAFF_ROLE)
        return Backup._can(user, need, submission.backup.get() if submission else None, query)


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
            file_comments = all_comments.setdefault(comment.filename, {})
            file_comments.setdefault(comment.line, []).append(comment)

        data['comments'] = all_comments
        return data
    
    @classmethod
    def _can(cls, user, need, diff, query):
        return Backup._can(
            user, 
            need, 
            diff.after.get() if diff else None, 
            None)


class Comment(Base):
    """A comment is part of a diff. The key has the diff as its parent."""
    author = ndb.KeyProperty(User)
    diff = ndb.KeyProperty(Diff)
    filename = ndb.StringProperty()
    line = ndb.IntegerProperty()
    # TODO Populate submission_line so that when diffs are changed, comments
    #      don't move around.
    submission_line = ndb.IntegerProperty()
    message = ndb.TextProperty() # Markdown

    @classmethod
    def _can(cls, user, need, comment=None, query=None):
        if user.is_admin:
          return True
        if need.action in ["get", "modify", "delete"]:
            return comment.author == user.key
        return False

    @classmethod
    def _can(cls, user, need, comment, query):
        return Diff._can(
            user, 
            need, 
            comment.diff.get() if comment else None,
            None)


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
        inst = cls(key=ndb.Key(cls._get_kind(), values['name']))
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

    Specification:
    https://github.com/Cal-CS-61A-Staff/ok/wiki/Group-&-Submission-Consistency
    """
    member = ndb.KeyProperty(User, repeated=True)
    invited = ndb.KeyProperty(User, repeated=True)
    assignment = ndb.KeyProperty(Assignment, required=True)
    order = ndb.StringProperty()

    @classmethod
    def lookup(cls, user_key, assignment_key):
        """Return the group for a user key."""
        if isinstance(user_key, User):
            user_key = user_key.key
        if isinstance(assignment_key, Assignment):
            assignment_key = assignment_key.key
        return Group.query(ndb.OR(Group.member == user_key,
                                  Group.invited == user_key),
                           Group.assignment == assignment_key).get()

    @classmethod
    def _lookup_or_create(cls, user_key, assignment_key):
        """Retrieve a group for user or create a group. Group is *not* put."""
        group = cls.lookup(user_key, assignment_key)
        if group:
            return group
        if isinstance(user_key, User):
            user_key = user_key.key
        if isinstance(assignment_key, Assignment):
            assignment_key = assignment_key.key
        return Group(member=[user_key], invited=[], assignment=assignment_key)

    @classmethod
    def lookup_by_assignment(cls, assignment):
        """ Returns all groups with the given assignment """
        if isinstance(assignment, Assignment):
            assign_key = assignment.key
        return Group.query(Group.assignment == assign_key).fetch()

    #@ndb.transactional
    def invite(self, email):
        """Invites a user to the group. Returns an error message or None."""
        if isinstance(email, ndb.Key):
            user = email.get()
            email = user.email[0]
        else:
            user = User.lookup(email)
        if not user:
            return "{} is not a valid user".format(email)
        course = self.assignment.get().course
        if not Participant.has_role(user, course, STUDENT_ROLE):
            return "{} is not enrolled in {}".format(email, course.get().display_name)
        if user.key in self.invited:
            return '{} has already been invited'.format(email)
        if user.key in self.member:
            return "{} is already in the group".format(email)
        has_user = ndb.OR(Group.member == user.key, Group.invited == user.key)
        if Group.query(has_user, Group.assignment == self.assignment).get():
            return "{} is already in some other group".format(email)
        max_group_size = self.assignment.get().max_group_size
        total_member = len(self.member) + len(self.invited)
        if total_member + 1 > max_group_size:
            return "The group is full"
        self.invited.append(user.key)
        self.put()
        for member in self.member:
            member.get().update_final_submission(self.assignment, self)

    #@ndb.transactional
    @classmethod
    def invite_to_group(cls, user_key, email, assignment_key):
        """User invites email to join his/her group. Returns error or None."""
        group = cls._lookup_or_create(user_key, assignment_key)
        if isinstance(user_key, User):
            user_key = user_key.key
        if isinstance(assignment_key, Assignment):
            assignment_key = assignment_key.key
        AuditLog(
            event_type='Group.invite',
            user=user_key,
            assignment=assignment_key,
            description='Added {} to group'.format(email),
            obj=group.key,
        ).put()
        return group.invite(email)

    #@ndb.transactional
    def accept(self, user_key):
        """User accepts an invitation to join. Returns error or None."""
        if isinstance(user_key, User):
            user_key = user_key.key
        if user_key not in self.invited:  # Note: these will never happen, according to _can
            return "That user is not invited to the group"
        if user_key in self.member:
            return "That user has already accepted."
        self.invited.remove(user_key)
        self.member.append(user_key)
        self.put()
        for user_key in self.member:
            user_key.get().update_final_submission(self.assignment, self)

    #@ndb.transactional
    def exit(self, user_key):
        """User leaves the group. Empty/singleton groups are deleted."""
        if isinstance(user_key, User):
            user_key = user_key.key
        if user_key not in self.member and user_key not in self.invited:
            return 'That user is not in this group and has not been invited.'
        for users in [self.member, self.invited]:
            if user_key in users:
                users.remove(user_key)

        error = self.validate()
        if error:
            subms = FinalSubmission.query(
                FinalSubmission.group==self.key
            ).fetch()
            for subm in subms:
                subm.group = None
                subm.put()
            self.key.delete()
        else:
            self.put()

        for user in self.member + [user_key]:
            user.get().update_final_submission(self.assignment)

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
        elif action in ("invite", "remove", "reorder"):
            return user.key in group.member
        elif action in "accept":
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

    def scores_for_assignment(self, assignment):
        """ Returns a list of lists containing score data
            for the groups's final submission for ASSIGNMENT. 
            There is one element for each combination of 
            group member and score.
            Ensures that each student only appears once in the list. 
            Format: [['STUDENT', 'SCORE', 'MESSAGE', 'GRADER', 'TAG']]
        """
        content = []
        for m in self.member:
            member = m.get()
            data, success = member.scores_for_assignment(assignment)
            content.extend(data)
            if success:
                # get_scores_for_student_or_group will return scores for all group members. 
                return content
        return [[member.email[0], 0, None, None, None]]



class AuditLog(Base):
    """Keeps track of Group changes that are happening. That way, we can stop
    cases of cheating by temporary access. (e.g. A is C's partner for 10 min
    so A can copy off of C)."""
    event_type = ndb.StringProperty()
    user = ndb.KeyProperty(User)
    assignment = ndb.KeyProperty(Assignment)
    description = ndb.StringProperty()
    obj = ndb.KeyProperty()


class Queue(Base):
    """A queue of submissions to grade."""
    assignment = ndb.KeyProperty(Assignment)
    course = ndb.ComputedProperty(lambda q: q.assignment.get().course)
    assigned_staff = ndb.KeyProperty(User, repeated=True)
    owner = ndb.KeyProperty(User)

    @property
    def submissions(self):
        """
        Returns all the submissions in this queue.
        """
        query = FinalSubmission.query().filter(FinalSubmission.queue == self.key)
        return [fs for fs in query]

    @property
    def graded(self):
        """
        Returns the count of graded submissions in this queue.
        """
        return len([1 for fs in self.submissions if fs.submission.get().score])

    def to_json(self, fields=None):
        if not fields:
            fields = {}

        final_submissions = self.submissions
        subms = []
        submitters = ndb.get_multi(fs.submitter for fs in final_submissions)
        submissions = [fs.submission for fs in final_submissions]
        submissions = ndb.get_multi(submissions)
        groups = [fs.group for fs in final_submissions]
        groups = ndb.get_multi(filter(None, groups))
        groups = {v.key: v for v in groups}
        for i, fs in enumerate(final_submissions):
          submission = submissions[i]
          group = groups.get(fs.group)
          subms.append(
            {
             'id': fs.key.id(),
             'submission': submission.key.id(),
             'created': submission.created,
             'backup': submission.backup.id(),
             'submitter': submitters[i],
             'group': group,
             'score': submission.score,
            })
        owner_email = "Unknown"
        if self.owner.get():
          owner_email = self.owner.get().email[0]

        return {
            'submissions': subms,
            'count': len(final_submissions),
            'graded': len(filter(None, (subm.score for subm in submissions))),
            'assignment': {'id': self.assignment},
            'assigned_staff': [val.get() for val in self.assigned_staff],
            'owner': owner_email,
            'id': self.key.id()
        }

    @classmethod
    def _can(cls, user, need, queue, query=None):
        action = need.action
        if not user.logged_in:
            return False

        if action == "index":
            if user.is_admin:
                return query
            courses = [part.course for part in Participant.query(
                Participant.user == user.key,
                Participant.role == STAFF_ROLE).fetch()]
            if courses:
                return disjunction(
                    query, [(Queue.course == course) for course in courses])
            return False

        course = queue.assignment.get().course
        is_staff = user.is_admin or \
            Participant.has_role(user, course, STAFF_ROLE)
        if is_staff:
            return True

        return False


class FinalSubmission(Base):
    """The final submission for an assignment from a group.

    Specification:
    https://github.com/Cal-CS-61A-Staff/ok/wiki/Final-Submissions-and-Grading
    """
    assignment = ndb.KeyProperty(Assignment)
    group = ndb.KeyProperty(Group)
    submission = ndb.KeyProperty(Submission)
    revision = ndb.KeyProperty(Submission)
    queue = ndb.KeyProperty(Queue)
    server_time = ndb.ComputedProperty(lambda q: q.submission.get().server_time)
    # submitter = ndb.ComputedProperty(lambda q: q.submission.get().submitter.get())
    submitter = ndb.KeyProperty(User)
    published = ndb.BooleanProperty(default=False)

    @property
    def backup(self):
        """
        Return the associated backup.
        """
        return self.submission.get().backup.get()

    @property
    def assigned(self):
        """
        Return whether or not this assignment has been assigned to a queue.
        """
        return bool(self.queue)

    @classmethod
    def _can(cls, user, need, final, query):
        action = need.action
        if action in ("create", "put") and final:
            group = final.submission.get().backup.get().group
            if group:
              return user.logged_in and user.key in group.member
        return Submission._can(
            user, need, final.submission.get() if final else None, query)

    def _pre_put_hook(self):
        # TODO Remove when submitter is a computed property
        self.submitter = self.submission.get().submitter

    def get_scores(self):
        """
        Return a list of lists of the format [[student, score, message, grader, tag]]
        if the submission has been scored. Otherwise an empty list.
        If the submission is a group submission, there will be an element
        for each combination of student and score.
        """
        # TODO: get the most recent score for each tag.
        # Question: will all scores have a grader? In particular the scores from the autograder.
        all_scores = []
        if self.group:
            members = [member for member in self.group.get().member]
        else:
            members = [self.submitter]
        for member in members:
            email = member.get().email[0]
            for score in self.submission.get().score:
                all_scores.append([email,
                        score.score,
                        score.message,
                        score.grader.get().email[0],
                        score.tag])
        return all_scores
