from markdown import markdown

from server.constants import STAFF_ROLES
from server.models.db import db, Model, mysql

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

    @classmethod
    def can(cls, obj, user, action):
        if action == "create":
            return user.is_authenticated
        if user.is_admin:
            return True
        if not obj:
            return False
        if action == "view" and user.id in obj.backup.owners():
            # Only allow group members to view
            return True
        if action == "edit" and user.id == obj.author_id:
            # Only allow non-staff to delete their own comments
            return True
        return user.is_enrolled(obj.assignment.course.id, STAFF_ROLES)

    @property
    def formatted(self):
        return markdown(self.message)
