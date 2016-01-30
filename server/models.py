from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import PrimaryKeyConstraint, MetaData
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import aliased, backref
from werkzeug.exceptions import BadRequest

from flask.ext.login import UserMixin, AnonymousUserMixin
from flask.ext.cache import Cache
cache = Cache()

import functools
import csv
import json
from datetime import datetime as dt

from server.constants import VALID_ROLES, STUDENT_ROLE, STAFF_ROLES

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

class DictMixin(object):

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TimestampMixin(object):
    created = db.Column(db.DateTime, server_default=db.func.now())


class User(db.Model, UserMixin, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String())
    email = db.Column(db.String(), unique=True, nullable=False, index=True)
    is_admin = db.Column(db.Boolean(), default=False)
    sid = db.Column(db.String())  # SID or Login
    secondary = db.Column(db.String())  # Other usernames
    alt_email = db.Column(db.String())
    active = db.Column(db.Boolean(), default=True)

    def __repr__(self):
        return '<User %r>' % self.email

    # TODO: Cache enrollment queries
    def enrollments(self, roles=[STUDENT_ROLE]):
        return [e for e in self.participations if e.role in roles]

    def is_enrolled(self, course_id, roles=VALID_ROLES):
        for enroll in self.participations:
            if enroll.course_id == course_id and enroll.role in roles:
                return enroll
        return False

    @staticmethod
    def lookup(email):
        """Get a User with the given email address, or None."""
        return User.query.filter_by(email=email).one_or_none()


class Course(db.Model, TimestampMixin, DictMixin):
    id = db.Column(db.Integer(), primary_key=True)
    offering = db.Column(db.String(), unique=True)
    # offering - E.g., 'cal/cs61a/fa14
    institution = db.Column(db.String())  # E.g., 'UC Berkeley'
    display_name = db.Column(db.String())
    creator = db.Column(db.ForeignKey("user.id"))
    active = db.Column(db.Boolean(), default=True)

    def __repr__(self):
        return '<Course %r>' % self.offering

    def is_enrolled(self, user):
        return Enrollment.query.filter_by(
            user=user,
            course=self
        ).count() > 0


class Assignment(db.Model, TimestampMixin, DictMixin):
    """Assignments are particular to courses and have unique names.
        name - cal/cs61a/fa14/proj1
        display_name - Hog
        due_date - DEADLINE (Publically displayed)
        lock_date - DEADLINE+1 (Hard Deadline for submissions)
        url - cs61a.org/proj/hog/hog.zip
    """

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), index=True, unique=True)
    course_id = db.Column(db.ForeignKey("course.id"), index=True,
                          nullable=False)
    display_name = db.Column(db.String(), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    lock_date = db.Column(db.DateTime, nullable=False)
    creator = db.Column(db.ForeignKey("user.id"))
    url = db.Column(db.String())
    max_group_size = db.Column(db.Integer(), default=1)
    revisions = db.Column(db.Boolean(), default=False)
    autograding_key = db.Column(db.String())
    course = db.relationship("Course", backref="assignments")

    @hybrid_property
    def active(self):
        return dt.utcnow() < self.lock_date  # TODO : Ensure all times are UTC

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
        """Return a query for the backups that the list of usrs has for this
        assignment.
        """
        return Backup.query.filter(
            Backup.submitter_id.in_(user_ids),
            Backup.assignment_id == self.id,
            Backup.submit == False
        ).order_by(Backup.client_time.desc())

    def submissions(self, user_ids):
        """Return a query for the submission that the current user has for this
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

    def offering_name(self):
        """ Returns the assignment name without the course offering.
        """
        return self.name.replace(self.course.offering + '/', '')


class Enrollment(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.ForeignKey("user.id"), index=True, nullable=False)
    course_id = db.Column(db.ForeignKey("course.id"), index=True,
                          nullable=False)
    role = db.Column(db.Enum(*VALID_ROLES, name='role'), default=STUDENT_ROLE, nullable=False)

    user = db.relationship("User", backref="participations")
    course = db.relationship("Course", backref="participants")
    notes = db.Column(db.String()) # For Section Info etc.

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
        Enrollment.create(cid, [usr.id], role)

    @staticmethod
    @transaction
    def enroll_from_csv(cid, form):
        new_users, existing_uids = [], []
        rows = form.csv.data.splitlines()
        entries = list(csv.reader(rows))
        for usr in entries:
            email, name, sid, login, notes = usr
            usr_obj = User.lookup(email)
            if not usr_obj:
                usr_obj = User(email=email, name=name, sid=sid, secondary=login)
                new_users.append(usr_obj)
            else:
                usr_obj.name = name
                usr_obj.sid = sid
                usr_obj.secondary = login
                usr_obj.notes = notes
                existing_uids.append(usr_obj.id)

        db.session.add_all(new_users)
        db.session.commit()
        user_ids = [u.id for u in new_users] + existing_uids
        Enrollment.create(cid, user_ids, STUDENT_ROLE)
        return len(new_users), len(existing_uids)


    @staticmethod
    @transaction
    def create(cid, usr_ids=[], role=STUDENT_ROLE):
        new_records = []
        for usr_id in usr_ids:
            record = Enrollment.query.filter_by(user_id=usr_id,
                                                   course_id=cid).one_or_none()
            if record:
                record.role = role
            else:
                record = Enrollment(course_id=cid, user_id=usr_id, role=role)
                new_records.append(record)
        db.session.add_all(new_records)


class Message(db.Model, TimestampMixin, DictMixin):
    id = db.Column(db.Integer(), primary_key=True)
    backup_id = db.Column(db.ForeignKey("backup.id"), index=True)
    raw_contents = db.Column(db.String())
    kind = db.Column(db.String(), index=True)

    backup = db.relationship("Backup")

    @hybrid_property
    def contents(self):
        return json.loads(str(self.raw_contents))

    @contents.setter
    def contents(self, value):
        self.raw_contents = str(json.dumps(value))


class Backup(db.Model, TimestampMixin, DictMixin):
    id = db.Column(db.Integer(), primary_key=True)
    messages = db.relationship("Message")
    scores = db.relationship("Score")
    user = db.relationship("User")
    assign = db.relationship("Assignment")

    client_time = db.Column(db.DateTime())
    submitter_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    submit = db.Column(db.Boolean(), default=False)
    flagged = db.Column(db.Boolean(), default=False)

    submitter = db.relationship("User")
    assignment = db.relationship("Assignment")

    db.Index('idx_usrBackups', 'assignment', 'submitter', 'submit', 'flagged')
    db.Index('idx_usrFlagged', 'assignment', 'submitter', 'flagged')
    db.Index('idx_submittedBacks', 'assignment', 'submit')
    db.Index('idx_flaggedBacks', 'assignment', 'flagged')

    def can_view(self, user, member_ids, course):
        if user.is_admin:
            return True
        if user.id == self.submitter_id:
            return True

        # Allow group members to view
        if self.submitter_id in member_ids:
            return True

        # Allow staff members to view
        return user.is_enrolled(course.id, STAFF_ROLES)

    @staticmethod
    def statistics(self):
        db.session.query(Backup).from_statement(
            db.text("""SELECT date_trunc('hour', backup.created), count(backup.id)  FROM backup
            WHERE backup.created >= NOW() - '1 day'::INTERVAL
            GROUP BY date_trunc('hour', backup.created)
            ORDER BY date_trunc('hour', backup.created)""")).all()


class Score(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    backup = db.Column(db.ForeignKey("backup.id"), nullable=False)
    grader = db.Column(db.ForeignKey("user.id"), nullable=False)
    tag = db.Column(db.String(), nullable=False)
    score = db.Column(db.Float())
    message = db.Column(db.Text())


class Version(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), nullable=False)
    current_version = db.Column(db.String(), nullable=False)
    base_url = db.Column(db.String())


class Diff(db.Model, TimestampMixin):
    """A diff between two versions of the same project, with comments.
    A diff has three types of lines: insertions, deletions, and matches.
    Every insertion line is associated with a diff line.
    If BEFORE is None, the BACKUP is diffed against the Assignment template.
    """
    id = db.Column(db.Integer(), primary_key=True)
    backup = db.Column(db.ForeignKey("backup.id"), nullable=False)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    before = db.Column(db.ForeignKey("backup.id"))
    diff = db.Column(db.String()) # TODO : Remove Diff Object.
    comments = db.relationship('Comment')
    updated = db.Column(db.DateTime, onupdate=db.func.now())


class Comment(db.Model, TimestampMixin):
    """A comment is part of a diff. The key has the diff as its parent.
    The diff a reference to the backup it was originated from.
    Line is the line # on the Diff Object.
    Submission_line is the closest line on the submitted file.
    """
    id = db.Column(db.Integer(), primary_key=True)
    diff = db.Column(db.ForeignKey("diff.id"), nullable=False)
    backup = db.Column(db.ForeignKey("backup.id"), nullable=False)
    author = db.Column(db.ForeignKey("user.id"), nullable=False)
    filename = db.Column(db.String(), nullable=False)
    line = db.Column(db.Integer(), nullable=False)
    submission_line = db.Column(db.Integer())
    message = db.Column(db.Text())  # Markdown


class CommentBank(db.Model, TimestampMixin):
    """ CommentBank is a set of common comments for assignments.
    An assignment value of null applies to all assignments.
    The statistics column will be used by the frontend.
    """
    id = db.Column(db.Integer(), primary_key=True)
    assignment = db.Column(db.ForeignKey("assignment.id"), index=True)
    author = db.Column(db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text())  # Markdown
    frequency = db.Column(db.Integer())


class GradingTask(db.Model, TimestampMixin):
    """Each task represent a single submission assigned to a grader."""
    id = db.Column(db.Integer(), primary_key=True)
    assignment = db.Column(db.ForeignKey("assignment.id"), index=True,
                           nullable=False)
    backup = db.Column(db.ForeignKey("backup.id"), nullable=False)
    course = db.Column(db.ForeignKey("course.id"))
    primary_owner = db.Column(db.ForeignKey("user.id"), index=True)
    kind = db.Column(db.Text())  # e.g. "composition"
    description = db.Column(db.Text())  # e.g. "Helpful links for grading"

    def is_complete(self):
        return self.kind in [s.tag for s in self.backup.scores]


class GroupMember(db.Model, TimestampMixin):
    """A member of a group must accept the invite to join the group.
    Only members of a group can view each other's submissions.
    A user may only be invited or participate in a single group per assignment.
    The status value can be one of:
        pending - The user has been invited to the group.
        active  - The user accepted the invite and is part of the group.
    """
    __tablename__ = 'group_member'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'assignment_id', name='pk_GroupMember'),
    )
    status_values = ['pending', 'active']

    user_id = db.Column(db.ForeignKey("user.id"), nullable=False, index=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    group_id = db.Column(db.ForeignKey("group.id"), nullable=False, index=True)

    status = db.Column(db.Enum(*status_values, name="status"), index=True)
    updated = db.Column(db.DateTime, onupdate=db.func.now())

    user = db.relationship("User")
    assignment = db.relationship("Assignment")
    group = db.relationship("Group",
        backref=backref('members', cascade="all, delete-orphan"))


class Group(db.Model, TimestampMixin):
    """A group is a collection of users who are either members or invited.
    Groups are created when a member not in a group invites another member.
    Invited members may accept or decline invitations. Active members may
    revoke invitations and remove members (including themselves).
    A group must have at least 2 participants.
    Degenerate groups are deleted.
    """
    id = db.Column(db.Integer(), primary_key=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)

    assignment = db.relationship("Assignment")

    def size(self):
        return GroupMember.query.filter_by(group=self).count()

    def has_status(self, user, status):
        return GroupMember.query.filter_by(
            user=user,
            group=self,
            status=status
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
        if not group:
            group = Group(assignment=assignment)
            db.session.add(group)
            group._add_member(sender, 'active')
        elif not group.has_status(sender, 'active'):
            raise BadRequest('You are not in the group')
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
        member.status = 'active'
        self.assignment._unflag_all(self.assignment.active_user_ids(user.id))

    @transaction
    def decline(self, user):
        """Decline an invitation."""
        if not self.assignment.active:
            raise BadRequest('The assignment is past due')
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
            user=user,
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
