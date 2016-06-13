# TODO: Split models into distinct .py files
from werkzeug.exceptions import BadRequest

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

from sqlalchemy import PrimaryKeyConstraint, MetaData, types
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import aliased, backref

import functools
import contextlib
import csv
from datetime import datetime as dt
import json
from markdown import markdown
import pytz

from server.constants import VALID_ROLES, STUDENT_ROLE, STAFF_ROLES
from server.extensions import cache
from server.utils import encode_id

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)

def transaction(f):
    """Decorator for database (session) transactions."""
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        try:
            value = f(*args, **kwds)
            db.session.commit()
            return value
        except:
            db.session.rollback()
            raise
    return wrapper


class Json(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return json.loads(value)

@compiles(mysql.MEDIUMBLOB, 'sqlite')
def ok_blob(element, compiler, **kw):
    return "BLOB"

@compiles(mysql.MEDIUMTEXT, 'sqlite')
def ok_text(element, compiler, **kw):
    return "TEXT"

class JsonBlob(types.TypeDecorator):
    impl = mysql.MEDIUMBLOB

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        return json.dumps(value).encode('utf-8')

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return json.loads(value.decode('utf-8'))


class Timezone(types.TypeDecorator):
    impl = types.String(255)

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        return value.zone

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return pytz.timezone(value)

class Model(db.Model):
    """Timestamps all models, and serializes model objects."""
    __abstract__ = True

    created = db.Column(db.DateTime(timezone=True),
                        server_default=db.func.now(), nullable=False)
    def __repr__(self):
        if hasattr(self, 'id'):
            key_val = self.id
        else:
            key_val = self.__mapper__.primary_key._list[0].name
        return '<{} {}>'.format(self.__class__.__name__, key_val)

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        return False

    @hybrid_property
    def export(self):
        """ CSV export data. """
        if not hasattr(self, 'export_items'):
            return {}
        return {k: v for k, v in self.as_dict().items() if k in self.export_items}

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class User(Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    is_admin = db.Column(db.Boolean(), default=False)

    def __repr__(self):
        return '<User {}>'.format(self.email)

    def enrollments(self, roles=[STUDENT_ROLE]):
        query = (Enrollment.query.options(db.joinedload('course'))
                           .filter(Enrollment.user_id == self.id)
                           .filter(Enrollment.role.in_(roles)))
        return query.all()

    @cache.memoize(120)
    def is_enrolled(self, course_id, roles=VALID_ROLES):
        for enroll in self.participations:
            if enroll.course_id == course_id and enroll.role in roles:
                return enroll
        return False

    def identifier(self):
        return self.name or self.email

    @cache.memoize(120)
    def num_grading_tasks(self):
        return GradingTask.query.filter_by(grader=self, score_id=None).count()

    @staticmethod
    def get_by_id(uid):
        """ Performs .query.get; potentially can be cached. """
        return User.query.get(uid)

    @staticmethod
    @cache.memoize(240)
    def email_by_id(uid):
        user = User.query.get(uid)
        if user:
            return user.email

    @staticmethod
    def lookup(email):
        """Get a User with the given email address, or None."""
        return User.query.filter_by(email=email).one_or_none()

class Course(Model):
    id = db.Column(db.Integer, primary_key=True)
    # offering - E.g., 'cal/cs61a/fa14'
    offering = db.Column(db.String(255), nullable=False, unique=True, index=True)
    institution = db.Column(db.String(255), nullable=False)  # E.g., 'UC Berkeley'
    display_name = db.Column(db.String(255), nullable=False)
    creator_id = db.Column(db.ForeignKey("user.id"))
    active = db.Column(db.Boolean(), nullable=False, default=True)
    timezone = db.Column(Timezone, nullable=False, default=pytz.timezone('America/Los_Angeles'))

    def __repr__(self):
        return '<Course %r>' % self.offering

    @staticmethod
    def by_name(name):
        return Course.query.filter_by(offering=name).one_or_none()

    @property
    def display_name_with_semester(self):
        year = self.offering[-2:]
        if "fa" in self.offering[-4:]:
            semester = "Fall"
        elif "sp" in self.offering[-4:]:
            semester = "Spring"
        else:
            semester = "Summer"
        return self.display_name + " ({0} 20{1})".format(semester, year)

    def is_enrolled(self, user):
        return Enrollment.query.filter_by(
            user=user,
            course=self
        ).count() > 0

    def get_staff(self):
        return [e for e in (Enrollment.query
                            .options(db.joinedload('user'))
                            .filter(Enrollment.role.in_(STAFF_ROLES),
                                    Enrollment.course == self)
                            .all()
                            )]

class Assignment(Model):
    """Assignments are particular to courses and have unique names.
        name - cal/cs61a/fa14/proj1
        display_name - Hog
        due_date - DEADLINE (Publically displayed)
        lock_date - DEADLINE+1 (Hard Deadline for submissions)
        url - cs61a.org/proj/hog/hog.zip
        flagged - User has indicated this one should be graded and not others
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index=True, nullable=False, unique=True)
    course_id = db.Column(db.ForeignKey("course.id"), index=True,
                          nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    due_date = db.Column(db.DateTime(timezone=True), nullable=False)
    lock_date = db.Column(db.DateTime(timezone=True), nullable=False)
    creator_id = db.Column(db.ForeignKey("user.id"))
    url = db.Column(db.Text)
    max_group_size = db.Column(db.Integer(), nullable=False, default=1)
    revisions_allowed = db.Column(db.Boolean(), nullable=False, default=False)
    autograding_key = db.Column(db.String(255))
    files = db.Column(JsonBlob)  # JSON object mapping filenames to contents
    course = db.relationship("Course", backref="assignments")

    @hybrid_property
    def active(self):
        return dt.utcnow() <= self.lock_date

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        if action == "view":
            return user.is_authenticated()
        return user.is_enrolled(obj.course.id, STAFF_ROLES)

    @staticmethod
    @cache.memoize(900)
    def assignment_stats(assign_id):
        assignment = Assignment.query.get(assign_id)
        base_query = Backup.query.filter_by(assignment=assignment)
        stats = {
            'submissions': base_query.filter_by(submit=True).count(),
            'backups': base_query.count(),
            'groups': Group.query.filter_by(assignment=assignment).count(),
        }
        # This is query intesive, maybe save for detailed stats?
        # students, submissions, not_started = assignment.course_submissions()
        # stats.update({
        #     'students_submitted': len(students),
        #     'students_nosubmit': len(not_started)
        # })
        return stats

    @staticmethod
    @cache.memoize(1000)
    def name_to_assign_info(name):
        assign = Assignment.query.filter_by(name=name).one_or_none()
        if assign:
            info = assign.as_dict()
            info['active'] = assign.active
            return info

    @staticmethod
    def by_name(name):
        """Return assignment object when given a name."""
        return Assignment.query.filter_by(name=name).one_or_none()

    def course_submissions(self):
        seen = set()
        students, submissions, no_submissions = set(), set(), set()
        for student in self.course.participations:
            if student.role == STUDENT_ROLE and student.user_id not in seen:
                group = self.active_user_ids(student.user_id)
                fs = self.final_submission(group)
                seen |= group  # Perform union of two sets
                if fs:
                    students |= group
                    submissions.add(fs.id)
                else:
                    no_submissions |= group
        return students, submissions, no_submissions

    def active_user_ids(self, user_id):
        """Return a set of the ids of all users that are active in the same group
        that our user is active in. If the user is not in a group, return just
        that user's id (i.e. as if they were in a 1-person group).
        """
        user_member = aliased(GroupMember)
        members = GroupMember.query.join(
            user_member, GroupMember.group_id == user_member.group_id
        ).filter(
            user_member.user_id == user_id,
            user_member.assignment_id == self.id,
            user_member.status == 'active',
            GroupMember.status == 'active'
        ).all()
        if not members:
            return {user_id}
        else:
            return {member.user_id for member in members}

    def backups(self, user_ids):
        """Return a query for the backups that the list of users has for this
        assignment.
        """
        return Backup.query.filter(
            Backup.submitter_id.in_(user_ids),
            Backup.assignment_id == self.id,
            Backup.submit == False
        ).order_by(Backup.created.desc())

    def submissions(self, user_ids):
        """Return a query for the submissions that the list of users has for this
        assignment.
        """
        return Backup.query.filter(
            Backup.submitter_id.in_(user_ids),
            Backup.assignment_id == self.id,
            Backup.submit == True
        ).order_by(Backup.created.desc())

    def final_submission(self, user_ids):
        """Return a final submission for a user, or None."""
        return Backup.query.filter(
            Backup.submitter_id.in_(user_ids),
            Backup.assignment_id == self.id,
            Backup.submit == True
        ).order_by(Backup.flagged.desc(), Backup.created.desc()).first()

    @transaction
    def flag(self, backup_id, member_ids):
        """Flag a submission. First unflags any submissions by one of
        MEMBER_IDS, which is a list of group member user IDs.
        """
        self._unflag_all(member_ids)
        backup = Backup.query.filter(
            Backup.id == backup_id,
            Backup.submitter_id.in_(member_ids),
            Backup.flagged == False
        ).one_or_none()
        if not backup:
            raise BadRequest('Could not find backup')
        backup.flagged = True

    @transaction
    def unflag(self, backup_id, member_ids):
        """Unflag a submission."""
        backup = Backup.query.filter(
            Backup.id == backup_id,
            Backup.submitter_id.in_(member_ids),
            Backup.flagged == True
        ).one_or_none()
        if not backup:
            raise BadRequest('Could not find backup')
        backup.flagged = False

    def _unflag_all(self, member_ids):
        """Unflag all submissions by members of MEMBER_IDS."""
        # There should only ever be one flagged submission
        backup = Backup.query.filter(
            Backup.submitter_id.in_(member_ids),
            Backup.flagged == True
        ).one_or_none()
        if backup:
            backup.flagged = False

class Enrollment(Model):
    __tablename__ = 'enrollment'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'course_id'),
    )

    user_id = db.Column(db.ForeignKey("user.id"), index=True, nullable=False)
    course_id = db.Column(db.ForeignKey("course.id"), index=True,
                          nullable=False)
    role = db.Column(db.Enum(*VALID_ROLES, name='role'),
                     default=STUDENT_ROLE, nullable=False)
    sid = db.Column(db.String(255))
    class_account = db.Column(db.String(255))
    section = db.Column(db.String(255))

    user = db.relationship("User", backref="participations")
    course = db.relationship("Course", backref="participations")

    export_items = ('sid', 'class_account', 'section')

    def has_role(self, course, role):
        if self.course != course:
            return False
        return self.role == role

    def is_staff(self, course):
        return self.course == course and self.role in STAFF_ROLES

    @staticmethod
    @transaction
    def enroll_from_form(cid, form):
        usr = User.lookup(form.email.data)
        if usr:
            form.populate_obj(usr)
        else:
            usr = User()
            form.populate_obj(usr)
            db.session.add(usr)
        db.session.commit()
        role = form.role.data
        info = {
            'id': usr.id,
            'sid': form.sid.data,
            'class_account': form.secondary.data,
            'section': form.section.data
        }
        Enrollment.create(cid, [info], role)

    @staticmethod
    @transaction
    def enroll_from_csv(cid, form):
        enrollment_info = []
        rows = form.csv.data.splitlines()
        entries = list(csv.reader(rows))
        new_users = []
        existing_user_count = 0
        for usr in entries:
            email, name, sid, login, section = usr
            usr_obj = User.lookup(email)
            user_info = {
                "sid": sid,
                "class_account": login,
                "section": section
            }
            if not usr_obj:
                usr_obj = User(email=email, name=name)
                new_users.append(usr_obj)
            else:
                usr_obj.name = name
                existing_user_count += 1
            user_info['id'] = usr_obj
            enrollment_info.append(user_info)

        db.session.add_all(new_users)
        db.session.commit()
        for info in enrollment_info:
            info['id'] = info['id'].id
        Enrollment.create(cid, enrollment_info, STUDENT_ROLE)
        return len(new_users), existing_user_count

    @staticmethod
    @transaction
    def create(cid, enrollment_info=[], role=STUDENT_ROLE):
        new_records = []
        for info in enrollment_info:
            usr_id, sid = info['id'], info['sid']
            class_account, section = info['class_account'], info['section']
            record = Enrollment.query.filter_by(user_id=usr_id,
                                                course_id=cid).one_or_none()
            if not record:
                record = Enrollment(course_id=cid, user_id=usr_id)
                new_records.append(record)

            record.role = role
            record.sid = sid
            record.class_account = class_account
            record.section = section

        db.session.add_all(new_records)

        cache.delete_memoized(User.is_enrolled)

class Message(Model):
    __tablename__ = 'message'
    __table_args__ = {'mysql_row_format': 'COMPRESSED'}

    id = db.Column(db.Integer, primary_key=True)
    backup_id = db.Column(db.ForeignKey("backup.id"), nullable=False,
                          index=True)
    contents = db.Column(JsonBlob, nullable=False)
    kind = db.Column(db.String(255), nullable=False, index=True)

    backup = db.relationship("Backup")


class Backup(Model):
    id = db.Column(db.Integer, primary_key=True)

    submitter_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    submit = db.Column(db.Boolean(), nullable=False, default=False)
    flagged = db.Column(db.Boolean(), nullable=False, default=False)

    extension = db.Column(db.Boolean(), default=False)

    submitter = db.relationship("User")
    assignment = db.relationship("Assignment")
    messages = db.relationship("Message")
    scores = db.relationship("Score")
    comments = db.relationship("Comment", order_by="Comment.created")

    db.Index('idx_usrBackups', 'submitter_id', 'assignment_id', 'submit', 'flagged')
    db.Index('idx_usrFlagged', 'submitter_id', 'assignment_id', 'flagged')
    db.Index('idx_submittedBacks', 'assignment_id', 'submit')
    db.Index('idx_flaggedBacks', 'assignment_id', 'flagged')

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        if action == "create":
            return user.is_authenticated()
        if not obj:
            return False
        if action == "view":
            # Only allow group members to view
            if user.id in obj.owners():
                return True
        return user.is_enrolled(obj.assignment.course.id, STAFF_ROLES)

    @hybrid_property
    def hashid(self):
        return encode_id(self.id)

    @hybrid_property
    def is_late(self):
        """ Check for manual extension before checking due date.
        """
        if self.extension:
            return False
        return self.created > self.assignment.due_date

    # @hybrid_property
    # def group(self):
    #     return Group.lookup(self.submitter, self.assignment)

    def owners(self):
        """ Return a set of user ids in the same group as the submitter."""
        return self.assignment.active_user_ids(self.submitter_id)

    def enrollment_info(self):
        """ Return enrollment info of users in this group.
        """
        owners = self.owners()
        course_id = self.assignment.course_id
        submitters = (Enrollment.query.options(db.joinedload(Enrollment.user))
                                .filter(Enrollment.user_id.in_(owners))
                                .filter(Enrollment.course_id == course_id)
                                .all())
        return submitters

    def files(self):
        """Return a dictionary of filenames to contents."""
        message = Message.query.filter_by(
            backup_id=self.id,
            kind='file_contents').first()
        if message:
            contents = dict(message.contents)
            # submit is not a real file, but the client sends it anyway
            contents.pop('submit', None)
            return contents
        else:
            return {}

    @staticmethod
    @cache.memoize(120)
    def statistics(self):
        return db.session.query(Backup).from_statement(
            db.text("""SELECT date_trunc('hour', backup.created), count(backup.id) FROM backup
            WHERE backup.created >= NOW() - '1 day'::INTERVAL
            GROUP BY date_trunc('hour', backup.created)
            ORDER BY date_trunc('hour', backup.created)""")).all()


class GroupMember(Model):
    """A member of a group must accept the invite to join the group.
    Only members of a group can view each other's submissions.
    A user may only be invited or participate in a single group per assignment.
    The status value can be one of:
        pending - The user has been invited to the group.
        active  - The user accepted the invite and is part of the group.
    """
    __tablename__ = 'group_member'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'assignment_id'),
    )
    status_values = ['pending', 'active']

    user_id = db.Column(db.ForeignKey("user.id"), nullable=False, index=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    group_id = db.Column(db.ForeignKey("group.id"), nullable=False, index=True)

    status = db.Column(db.Enum(*status_values, name="status"), nullable=False, index=True)
    updated = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    user = db.relationship("User")
    assignment = db.relationship("Assignment")
    group = db.relationship("Group", backref=backref('members',
                                                     cascade="all, delete-orphan"))


class Group(Model):
    """A group is a collection of users who are either members or invited.
    Groups are created when a member not in a group invites another member.
    Invited members may accept or decline invitations. Active members may
    revoke invitations and remove members (including themselves).
    A group must have at least 2 participants.
    Degenerate groups are deleted.
    """
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)

    assignment = db.relationship("Assignment")

    def size(self, status=None):
        return GroupMember.query.filter_by(group=self).count()

    def has_status(self, user, status):
        return GroupMember.query.filter_by(
            user=user,
            group=self,
            status=status
        ).count() > 0

    def is_pending(self):
        """ Returns a boolean indicating if group has an invitation pending.
        """
        return GroupMember.query.filter_by(
            group=self,
            status='pending'
        ).count() > 0

    def users(self):
        return [m.user for m in self.members]

    @staticmethod
    def lookup(user, assignment):
        member = GroupMember.query.filter_by(
            user=user,
            assignment=assignment
        ).one_or_none()
        if member:
            return member.group

    @staticmethod
    @transaction
    def invite(sender, recipient, assignment):
        """Invite a user to a group, creating a group if necessary."""
        if not assignment.active:
            raise BadRequest('The assignment is past due')
        group = Group.lookup(sender, assignment)
        add_sender = group is None
        if not group:
            group = Group(assignment=assignment)
            db.session.add(group)
        elif not group.has_status(sender, 'active'):
            raise BadRequest('You are not in the group')
        with group._log('invite', sender.id, recipient.id):
            if add_sender:
                group._add_member(sender, 'active')
            group._add_member(recipient, 'pending')

    @transaction
    def remove(self, user, target_user):
        """Remove a user from the group.
        The user must be an active member in the group, and the target user
        must be an active or pending member. You may remove yourself to leave
        the group. The assignment must also be active.
        """
        if not self.assignment.active:
            raise BadRequest('The assignment is past due')
        if not self.has_status(user, 'active'):
            raise BadRequest('You are not in the group')
        with self._log('remove', user.id, target_user.id):
            self._remove_member(target_user)

    @transaction
    def accept(self, user):
        """Accept an invitation."""
        if not self.assignment.active:
            raise BadRequest('The assignment is past due')
        member = GroupMember.query.filter_by(
            user=user,
            group=self,
            status='pending'
        ).one_or_none()
        if not member:
            raise BadRequest('{0} is not invited to this group'.format(user.email))
        with self._log('accept', user.id, user.id):
            member.status = 'active'
        self.assignment._unflag_all(self.assignment.active_user_ids(user.id))

    @transaction
    def decline(self, user):
        """Decline an invitation."""
        if not self.assignment.active:
            raise BadRequest('The assignment is past due')
        with self._log('decline', user.id, user.id):
            self._remove_member(user)

    def _add_member(self, user, status):
        if self.size() >= self.assignment.max_group_size:
            raise BadRequest('This group is full')
        if not self.assignment.course.is_enrolled(user):
            raise BadRequest('{0} is not enrolled'.format(user.email))
        member = GroupMember.query.filter_by(
            user=user,
            assignment=self.assignment
        ).one_or_none()
        if member:
            raise BadRequest('{0} is already in this group'.format(user.email))
        member = GroupMember(
            user_id=user.id,
            group=self,
            assignment=self.assignment,
            status=status)
        db.session.add(member)

    def _remove_member(self, user):
        member = GroupMember.query.filter_by(
            user=user,
            group=self
        ).one_or_none()
        if not member:
            raise BadRequest('{0} is not in this group'.format(user.email))
        db.session.delete(member)
        if self.size() <= 1:
            db.session.delete(self)

    def serialize(self):
        """Turn the group into a JSON object with:
        - id: the group id
        - assignment_id: the assignment id
        - members: a list of objects, with keys
            - user_id: the user id
            - status: the user's status ("pending" or "active")
        """
        members = GroupMember.query.filter_by(group_id=self.id).all()
        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'members': [{
                'user_id': member.user_id,
                'status': member.status
            } for member in members]
        }

    @contextlib.contextmanager
    def _log(self, action_type, user_id, target_id):
        """Usage:

        with self._log('invite', user_id, target_id):
            ...
        """
        before = self.serialize()
        yield
        after = self.serialize()
        action = GroupAction(
            action_type=action_type,
            user_id=user_id,
            target_id=target_id,
            group_before=before,
            group_after=after)
        db.session.add(action)


class GroupAction(Model):
    """A group event, for auditing purposes. All group activity is logged."""
    action_types = ['invite', 'accept', 'decline', 'remove']

    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.Enum(*action_types, name='action_type'), nullable=False)
    # user who initiated request
    user_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    # user whose status was affected
    target_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    # see Group.serialize for format
    group_before = db.Column(Json, nullable=False)
    group_after = db.Column(Json, nullable=False)

class Version(Model):
    id = db.Column(db.Integer(), primary_key=True)
    # software name e.g. 'ok'
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    current_version = db.Column(db.String(255))
    download_link = db.Column(db.Text())

    @staticmethod
    @cache.memoize(1000)
    def get_current_version(name):
        version = Version.query.filter_by(name=name).one_or_none()
        if version:
            return version.current_version, version.download_link
        return None, None

class Comment(Model):
    """ Composition comments. Line is the line # on the Diff.
    Submission_line is the closest line on the submitted file.
    """
    id = db.Column(db.Integer(), primary_key=True)
    updated = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())
    backup_id = db.Column(db.ForeignKey("backup.id"), index=True, nullable=False)
    author_id = db.Column(db.ForeignKey("user.id"), nullable=False)

    filename = db.Column(db.String(255), nullable=False)
    line = db.Column(db.Integer(), nullable=False)  # Line of the original file

    message = db.Column(mysql.MEDIUMTEXT)  # Markdown

    backup = db.relationship("Backup")
    author = db.relationship("User")

    @property
    def formatted(self):
        return markdown(self.message)

class Score(Model):
    id = db.Column(db.Integer, primary_key=True)
    grader_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    backup_id = db.Column(db.ForeignKey("backup.id"), nullable=False, index=True)

    kind = db.Column(db.String(255), nullable=False)
    score = db.Column(db.Float, nullable=False)
    message = db.Column(mysql.MEDIUMTEXT)
    public = db.Column(db.Boolean, default=True)
    archived = db.Column(db.Boolean, default=False)

    backup = db.relationship("Backup")
    grader = db.relationship("User")
    assignment = db.relationship("Assignment")

    export_items = ('assignment_id', 'kind', 'score', 'message',
                    'backup_id', 'grader')

    @hybrid_property
    def export(self):
        """ CSV export data. Overrides Model.export """
        data = self.as_dict()
        data['backup_id'] = encode_id(self.backup_id)
        data['grader'] = User.email_by_id(self.grader_id)
        return {k: v for k, v in data.items() if k in self.export_items}

    @hybrid_property
    def students(self):
        """ The users to which this score applies. """
        return [User.query.get(owner) for owner in self.backup.owners()]

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        course = obj.assignment.course
        if action == "get":
            return obj.backup.can_view(user, course)
        return user.is_enrolled(course.id, STAFF_ROLES)

class GradingTask(Model):
    """Each task represent a single submission assigned to a grader."""
    id = db.Column(db.Integer(), primary_key=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), index=True,
                              nullable=False)
    kind = db.Column(db.String(255), default="composition")
    backup_id = db.Column(db.ForeignKey("backup.id"), nullable=False)
    course_id = db.Column(db.ForeignKey("course.id"))
    grader_id = db.Column(db.ForeignKey("user.id"), index=True)
    score_id = db.Column(db.ForeignKey("score.id"))

    backup = db.relationship("Backup", backref="grading_tasks")
    assignment = db.relationship("Assignment")
    grader = db.relationship("User")
    course = db.relationship("Course")

    @hybrid_property
    def is_complete(self):
        return self.score_id is not None
        # return self.kind in [s.tag for s in self.backup.scores]
