from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects import postgresql as pg
from flask.ext.login import UserMixin, AnonymousUserMixin

from server.constants import VALID_ROLES, STUDENT_ROLE, STAFF_ROLES

db = SQLAlchemy()


class TimestampMixin(object):
    created = db.Column(db.DateTime, server_default=db.func.now())


class User(db.Model, UserMixin, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    email = db.Column(db.String(), unique=True, nullable=False, index=True)
    is_admin = db.Column(db.Boolean(), default=False)
    sid = db.Column(db.String())  # SID or Login
    secondary = db.Column(db.String())  # Other usernames
    alt_email = db.Column(db.String())
    active = db.Column(db.Boolean(), default=True)

    def __init__(self, email, name=None, sid=None):
        self.email = email
        self.sid = sid

    def check_login(self, value):
        return value and self.access_token == value

    def is_authenticated(self):
        if isinstance(self, AnonymousUserMixin):
            return False
        else:
            return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        if isinstance(self, AnonymousUserMixin):
            return True
        else:
            return False

    def get_id(self):
        return self.id

    def __repr__(self):
        return '<User %r>' % self.email


class Course(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    offering = db.Column(db.String(), unique=True, index=True)
    # offering - E.g., 'cal/cs61a/fa14
    institution = db.Column(db.String())  # E.g., 'UC Berkeley'
    display_name = db.Column(db.String())
    creator = db.Column(db.ForeignKey("user.id"))
    active = db.Column(db.Boolean(), default=True)

    def __repr__(self):
        return '<Course %r>' % self.offering


class Assignment(db.Model, TimestampMixin):
    """Assignments are particular to courses and have unique names.
        name - cal/cs61a/fa14/proj1
        display_name - Hog
        due_date - DEADLINE (Publically displayed)
        lock_date - DEADLINE+1 (Hard Deadline for submissions)
        url - cs61a.org/proj/hog/hog.zip
    """

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(), index=True, unique=True)
    course = db.Column(db.ForeignKey("course.id"), index=True, nullable=False)
    display_name = db.Column(db.String(), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    lock_date = db.Column(db.DateTime, nullable=False)
    creator = db.Column(db.ForeignKey("user.id"))
    url = db.Column(db.String())
    max_group_size = db.Column(db.Integer(), default=1)
    revisions = db.Column(db.Boolean(), default=False)
    autograding_key = db.Column(db.String())

    # TODO Active property
    def active(self):
        return db.func.now() < self.lock_date


class Participant(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    user = db.Column(db.ForeignKey("user.id"), index=True, nullable=False)
    course = db.Column(db.ForeignKey("course.id"), index=True, nullable=False)
    role = db.Column(db.Enum(*VALID_ROLES, name='role'), nullable=False)

    def __init__(self, user, course, role=STUDENT_ROLE):
        self.user = user
        self.course = course
        self.role = role

    def has_role(self, course, role):
        if self.course != course:
            return False
        return self.role == role

    def is_staff(self, course):
        return self.course == course and self.role in STAFF_ROLES


class Message(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    backup = db.Column(db.ForeignKey("backup.id"), index=True)
    contents = db.Column(pg.JSONB())
    kind = db.Column(db.String(), index=True)

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Backup(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    messages = db.relationship("Message")
    scores = db.relationship("Score")
    client_time = db.Column(db.DateTime())
    submitter = db.Column(db.ForeignKey("user.id"), nullable=False)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)

    db.Index('idx_backAUser', 'assignment', 'submitter'),

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Submission(db.Model, TimestampMixin):
    id = db.Column(db.Integer(), primary_key=True)
    backup = db.Column(db.ForeignKey("backup.id"), nullable=False)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    submitter = db.Column(db.ForeignKey("user.id"), nullable=False)
    queue = db.Column(db.ForeignKey("queue.id"))
    flagged = db.Column(db.Boolean(), default=False)
    revision = db.Column(db.ForeignKey("submission.id"))

    db.Index('idx_flaggedSubms', 'assignment', 'submitter', 'flagged'),


class FinalSubmission(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    submission = db.Column(db.ForeignKey("submission.id"), nullable=False)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)

    @property
    def created(self):
        return self.submission.created


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
    versions = db.Column(pg.ARRAY(db.String()), nullable=False)
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
    diff = db.Column(pg.JSONB())
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


class Queue(db.Model, TimestampMixin):
    """A queue of submissions to grade."""
    id = db.Column(db.Integer(), primary_key=True)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    course = db.Column(db.ForeignKey("course.id"), nullable=False)
    primary_owner = db.Column(db.ForeignKey("user.id"), nullable=False)
    description = db.Column(db.Text())


class Group(db.Model, TimestampMixin):
    """A group is a collection of users who are either members or invited.

    Members of a group can view each other's submissions.

    Specification:
    https://github.com/Cal-CS-61A-Staff/ok/wiki/Group-&-Submission-Consistency
    """
    id = db.Column(db.Integer(), primary_key=True)
    assignment = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    members = db.Column(db.ForeignKey("user.id"), nullable=False)
    order = db.Column(db.String())

# TODO AuditLog
