from sqlalchemy.ext.hybrid import hybrid_property

from server.utils import encode_id
from server.constants import STAFF_ROLES
from server.models.db import db, Model
from server.extensions import cache

from server.models import Enrollment
from server.models import Message

class Backup(Model):
    id = db.Column(db.Integer, primary_key=True)

    submitter_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    # NULL if same as submitter
    creator_id = db.Column(db.ForeignKey("user.id"), nullable=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    submit = db.Column(db.Boolean(), nullable=False, default=False, index=True)
    flagged = db.Column(db.Boolean(), nullable=False, default=False, index=True)
    # The time we should treat this backup as being submitted. If NULL, use
    # the `created` timestamp instead.
    custom_submission_time = db.Column(db.DateTime(timezone=True), nullable=True)

    submitter = db.relationship("User", foreign_keys='Backup.submitter_id')
    creator = db.relationship("User", foreign_keys='Backup.creator_id')
    assignment = db.relationship("Assignment")
    messages = db.relationship("Message")
    scores = db.relationship("Score")
    comments = db.relationship("Comment", order_by="Comment.created")

    # Already have indexes for submitter_id and assignment_id due to FK
    db.Index('idx_backupCreated', 'created')

    @classmethod
    def can(cls, obj, user, action):
        if action == "create":
            return user.is_authenticated
        elif not obj:
            return False
        elif user.is_admin:
            return True
        elif action == "view" and user.id in obj.owners():
            # Only allow group members to view
            return True
        return user.is_enrolled(obj.assignment.course.id, STAFF_ROLES)

    @hybrid_property
    def hashid(self):
        return encode_id(self.id)

    @hybrid_property
    def is_late(self):
        return self.submission_time > self.assignment.due_date

    @hybrid_property
    def active_scores(self):
        """Return non-archived scores."""
        return [s for s in self.scores if not s.archived]

    @hybrid_property
    def published_scores(self):
        """Return non-archived scores that are published to students."""
        return [s for s in self.scores
            if not s.archived and s.kind in self.assignment.published_scores]

    @hybrid_property
    def is_revision(self):
        return any(s for s in self.scores if s.kind == "revision")

    @hybrid_property
    def submission_time(self):
        if self.custom_submission_time:
            return self.custom_submission_time
        return self.created

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
        """ Return a dictionary of filenames to contents."""
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

    def analytics(self):
        """ Return a dictionary of filenames to contents."""
        message = Message.query.filter_by(
            backup_id=self.id,
            kind='analytics').first()
        if message:
            return dict(message.contents)
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
