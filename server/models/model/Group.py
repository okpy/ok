import contextlib

from werkzeug.exceptions import BadRequest

from server.models.db import db, Model, transaction
from server.models import GroupMember
from server.models import GroupAction

class Group(Model):
    """ A group is a collection of users who are either members or invited.
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
    def force_add(staff, sender, recipient, assignment):
        """ Used by staff to create groups users on behalf of users."""
        group = Group.lookup(sender, assignment)
        add_sender = group is None
        if not group:
            group = Group(assignment=assignment)
            db.session.add(group)
        with group._log('accept', staff.id, recipient.id):
            if add_sender:
                group._add_member(sender, 'active')
            group._add_member(recipient, 'active')

    @staticmethod
    @transaction
    def force_remove(staff, sender, target, assignment):
        """ Used by staff to remove users."""
        group = Group.lookup(sender, assignment)
        if not group:
            raise BadRequest('No group to remove from')
        with group._log('remove', staff.id, target.id):
            group._remove_member(target)

    @staticmethod
    @transaction
    def invite(sender, recipient, assignment):
        """ Invite a user to a group, creating a group if necessary."""
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
        """ Remove a user from the group.
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
        """ Accept an invitation."""
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
        self.assignment._unflag_all([user.id])

    @transaction
    def decline(self, user):
        """ Decline an invitation."""
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
            raise BadRequest('{0} is already in a group'.format(user.email))
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
        """ Turn the group into a JSON object with:
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
        """ Usage:

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
