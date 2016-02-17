import datetime
from werkzeug.exceptions import BadRequest

from server.models import db, Assignment, Group, GroupAction, User

from tests import OkTestCase

class TestGroup(OkTestCase):
    def setUp(self):
        super(TestGroup, self).setUp()
        self.setup_course()

    def test_invite(self):
        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)

        assert group.has_status(self.user1, 'active')
        assert group.has_status(self.user2, 'pending')
        assert group.size() == 2

        Group.invite(self.user1, self.user3, self.assignment)

        assert group.has_status(self.user1, 'active')
        assert group.has_status(self.user2, 'pending')
        assert group.has_status(self.user3, 'pending')
        assert group.size() == 3

    def test_invite_not_enrolled(self):
        not_enrolled = User(email='not_enrolled@aol.com')
        db.session.add(not_enrolled)

        self.assertRaises(BadRequest, Group.invite, self.user1, not_enrolled, self.assignment)
        self.assertRaises(BadRequest, Group.invite, not_enrolled, self.user1, self.assignment)

    def test_invite_in_group(self):
        Group.invite(self.user1, self.user2, self.assignment)

        self.assertRaises(BadRequest, Group.invite, self.user1, self.user1, self.assignment)
        self.assertRaises(BadRequest, Group.invite, self.user1, self.user2, self.assignment)

        self.assertRaises(BadRequest, Group.invite, self.user2, self.user1, self.assignment)
        self.assertRaises(BadRequest, Group.invite, self.user2, self.user2, self.assignment)
        self.assertRaises(BadRequest, Group.invite, self.user2, self.user3, self.assignment)

        self.assertRaises(BadRequest, Group.invite, self.user3, self.user1, self.assignment)
        self.assertRaises(BadRequest, Group.invite, self.user3, self.user2, self.assignment)
        self.assertRaises(BadRequest, Group.invite, self.user3, self.user3, self.assignment)

    def test_invite_full(self):
        Group.invite(self.user1, self.user2, self.assignment)
        Group.invite(self.user1, self.user3, self.assignment)
        Group.invite(self.user1, self.user4, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        assert group.size() == 4
        self.assertRaises(BadRequest, Group.invite, self.user1, self.user5, self.assignment)

    def test_invite_individual(self):
        individual_assignment = Assignment(
            name='cal/cs61a/sp16/lab00',
            course=self.course,
            display_name='Lab 0',
            due_date=datetime.datetime.now(),
            lock_date=datetime.datetime.now() + datetime.timedelta(days=1),
            max_group_size=1)
        db.session.add(individual_assignment)

        self.assertRaises(BadRequest, Group.invite, self.user1, self.user2, individual_assignment)

    def test_locked(self):
        Group.invite(self.user1, self.user2, self.assignment)
        Group.invite(self.user1, self.user3, self.assignment)
        Group.invite(self.user1, self.user4, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        self.assignment.lock_date = datetime.datetime.now() - datetime.timedelta(days=1)
        db.session.commit()

        self.assertRaises(BadRequest, Group.invite, self.user1, self.user2, self.assignment)
        self.assertRaises(BadRequest, group.accept, self.user3)
        self.assertRaises(BadRequest, group.decline, self.user3)
        self.assertRaises(BadRequest, group.remove, self.user1, self.user2)

    def test_accept(self):
        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        assert group.has_status(self.user1, 'active')
        assert group.has_status(self.user2, 'active')
        assert group.size() == 2

    def test_accept_not_pending(self):
        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        self.assertRaises(BadRequest, group.accept, self.user2)
        self.assertRaises(BadRequest, group.accept, self.user3)

    def test_decline(self):
        Group.invite(self.user1, self.user2, self.assignment)
        Group.invite(self.user1, self.user3, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)
        group.decline(self.user3)

        assert group.has_status(self.user1, 'active')
        assert group.has_status(self.user2, 'active')
        assert Group.lookup(self.user3, self.assignment) is None
        assert group.size() == 2

    def test_decline_degenerate(self):
        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.decline(self.user2)

        assert Group.lookup(self.user1, self.assignment) is None
        assert Group.lookup(self.user2, self.assignment) is None

    def test_decline_not_pending(self):
        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)

        self.assertRaises(BadRequest, group.decline, self.user3)

    def test_remove(self):
        Group.invite(self.user1, self.user2, self.assignment)
        Group.invite(self.user1, self.user3, self.assignment)
        Group.invite(self.user1, self.user4, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        group.remove(self.user1, self.user2)
        assert group.has_status(self.user1, 'active')
        assert Group.lookup(self.user2, self.assignment) is None
        assert group.has_status(self.user3, 'pending')
        assert group.size() == 3

        group.remove(self.user1, self.user3)
        assert group.has_status(self.user1, 'active')
        assert Group.lookup(self.user3, self.assignment) is None
        assert group.size() == 2

    def test_remove_self(self):
        Group.invite(self.user1, self.user2, self.assignment)
        Group.invite(self.user1, self.user3, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)
        group.accept(self.user3)
        group.remove(self.user1, self.user1)

        assert Group.lookup(self.user1, self.assignment) is None
        assert group.has_status(self.user2, 'active')
        assert group.has_status(self.user3, 'active')

    def test_remove_degenerate(self):
        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.remove(self.user1, self.user1)

        assert Group.lookup(self.user1, self.assignment) is None
        assert Group.lookup(self.user2, self.assignment) is None

    def test_remove_not_in_group(self):
        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        self.assertRaises(BadRequest, group.remove, self.user2, self.user3)
        self.assertRaises(BadRequest, group.remove, self.user3, self.user2)

    def test_log(self):
        def latest_action():
            return GroupAction.query.order_by(GroupAction.id.desc()).first()

        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)

        state = {
            'id': group.id,
            'assignment_id': group.assignment_id,
            'members': []
        }

        action = latest_action()
        assert action.action_type == 'invite'
        assert action.user_id == self.user1.id
        assert action.target_id == self.user2.id
        assert action.group_before == state
        state['members'].append({
            'user_id': self.user1.id,
            'status': 'active'
        })
        state['members'].append({
            'user_id': self.user2.id,
            'status': 'pending'
        })
        assert action.group_after == state

        group.accept(self.user2)

        action = latest_action()
        assert action.action_type == 'accept'
        assert action.user_id == self.user2.id
        assert action.target_id == self.user2.id
        assert action.group_before == state
        state['members'][1]['status'] = 'active'
        assert action.group_after == state

        Group.invite(self.user1, self.user3, self.assignment)

        action = latest_action()
        assert action.action_type == 'invite'
        assert action.user_id == self.user1.id
        assert action.target_id == self.user3.id
        assert action.group_before == state
        state['members'].append({
            'user_id': self.user3.id,
            'status': 'pending'
        })
        assert action.group_after == state

        group.decline(self.user3)

        action = latest_action()
        assert action.action_type == 'decline'
        assert action.user_id == self.user3.id
        assert action.target_id == self.user3.id
        assert action.group_before == state
        state['members'].pop(2)
        assert action.group_after == state

        group.remove(self.user2, self.user1)
        action = latest_action()
        assert action.action_type == 'remove'
        assert action.user_id == self.user2.id
        assert action.target_id == self.user1.id
        assert action.group_before == state
        state['members'] = []
        assert action.group_after == state
