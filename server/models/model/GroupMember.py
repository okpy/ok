from sqlalchemy.orm import backref

from sqlalchemy import PrimaryKeyConstraint
from server.models.db import db, Model

class GroupMember(Model):
    """ A member of a group must accept the invite to join the group.
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
    status_enum = db.Enum(*status_values, name="status")

    user_id = db.Column(db.ForeignKey("user.id"), nullable=False, index=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    group_id = db.Column(db.ForeignKey("group.id"), nullable=False, index=True)
    status = db.Column(status_enum, nullable=False, index=True)
    updated = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    user = db.relationship("User")
    assignment = db.relationship("Assignment")
    group = db.relationship("Group", backref=backref('members',
                                                     cascade="all, delete-orphan"))
