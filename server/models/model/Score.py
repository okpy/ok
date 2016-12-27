from sqlalchemy.ext.hybrid import hybrid_property

from server.constants import STAFF_ROLES
from server.utils import encode_id

from server.models.db import db, Model, mysql, transaction
from server.models import User

class Score(Model):
    id = db.Column(db.Integer, primary_key=True)
    grader_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    backup_id = db.Column(db.ForeignKey("backup.id"), nullable=False, index=True)
    # submitter of score's backup
    user_id = db.Column(db.ForeignKey("user.id"), nullable=False)

    kind = db.Column(db.String(255), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    message = db.Column(mysql.MEDIUMTEXT)
    public = db.Column(db.Boolean, default=True)
    archived = db.Column(db.Boolean, default=False, index=True)

    backup = db.relationship("Backup")
    grader = db.relationship("User", foreign_keys='Score.grader_id')
    user = db.relationship("User", foreign_keys='Score.user_id')
    assignment = db.relationship("Assignment")

    export_items = ('assignment_id', 'kind', 'score', 'message',
                    'backup_id', 'grader')

    @hybrid_property
    def export(self):
        """ CSV export data. Overrides Model.export."""
        data = self.as_dict()
        data['backup_id'] = encode_id(self.backup_id)
        data['grader'] = User.email_by_id(self.grader_id)
        return {k: v for k, v in data.items() if k in self.export_items}

    @hybrid_property
    def students(self):
        """ The users to which this score applies."""
        return [User.query.get(owner) for owner in self.backup.owners()]

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        course = obj.assignment.course
        if action == "get":
            return obj.backup.can_view(user, course)
        return user.is_enrolled(course.id, STAFF_ROLES)

    def archive(self, commit=True):
        self.public = False
        self.archived = True

        if commit:
            db.session.commit()

    @transaction
    def archive_duplicates(self):
        """ Archive scores with of the same kind on the same backup.
        TODO: Investigate doing automatically on create/save.
        """
        existing_scores = Score.query.filter_by(backup=self.backup,
                                                kind=self.kind,
                                                archived=False).all()
        for old_score in existing_scores:
            if old_score.id != self.id:  # Do not archive current score
                old_score.archive(commit=False)
