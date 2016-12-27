from server.models.db import db, Model, Json

class GroupAction(Model):
    """ A group event, for auditing purposes. All group activity is logged."""
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
