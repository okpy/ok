from .helpers import OkTestCase

from server.models import db, Group

class TestSubmission(OkTestCase):
    """Tests querying for submissions and backups, flagging submissions, and
    final submissions.
    """
    def setUp(self):
        super(TestSubmission, self).setUp()
        self.setup_course()

    def test_active_user_ids(self):
        Group.invite(self.user1, self.user2, self.assignment)
        Group.invite(self.user1, self.user3, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        assert self.assignment.active_user_ids(self.user1.id) == \
            {self.user1.id, self.user2.id}
        assert self.assignment.active_user_ids(self.user2.id) == \
            {self.user1.id, self.user2.id}
        assert self.assignment.active_user_ids(self.user3.id) == \
            {self.user3.id}
