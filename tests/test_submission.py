import datetime
import json
from werkzeug.exceptions import BadRequest

from server.models import db, Backup, Group, Message

from .helpers import OkTestCase

class TestSubmission(OkTestCase):
    """Tests flagging submissions and final submissions."""
    def setUp(self):
        super(TestSubmission, self).setUp()
        self.setup_course()

        message_dict = {'file_contents': {'backup.py': '1'}, 'analytics': {}}

        self.active_user_ids = [self.user1.id, self.user2.id, self.user3.id]

        # create a submission every 15 minutes
        time = self.assignment.due_date
        for _ in range(20):
            for user_id in self.active_user_ids:
                time -= datetime.timedelta(minutes=15)
                backup = Backup(client_time=time,
                    submitter_id=user_id,
                    assignment=self.assignment, submit=True)
                messages = [Message(kind=k, backup=backup,
                    raw_contents=json.dumps(m)) for k, m in message_dict.items()]
                db.session.add_all(messages)
                db.session.add(backup)
        db.session.commit()

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

    def test_no_flags(self):
        final = self.assignment.final_submission(self.active_user_ids)
        most_recent = self.assignment.submissions(self.active_user_ids).first()
        assert final == most_recent

    def test_flag(self):
        submission = self.assignment.submissions(self.active_user_ids).all()[3]
        self.assignment.flag(submission.id, self.active_user_ids)

        final = self.assignment.final_submission(self.active_user_ids)
        assert final == submission

    def test_two_flags(self):
        submission1 = self.assignment.submissions(self.active_user_ids).all()[3]
        submission2 = self.assignment.submissions(self.active_user_ids).all()[7]
        self.assignment.flag(submission1.id, self.active_user_ids)
        self.assignment.flag(submission2.id, self.active_user_ids)

        final = self.assignment.final_submission(self.active_user_ids)
        assert final == submission2
        assert not submission1.flagged

    def test_unflag(self):
        submission = self.assignment.submissions(self.active_user_ids).all()[3]
        self.assignment.flag(submission.id, self.active_user_ids)
        self.assignment.unflag(submission.id, self.active_user_ids)

        final = self.assignment.final_submission(self.active_user_ids)
        most_recent = self.assignment.submissions(self.active_user_ids).first()
        assert final == most_recent
        assert not submission.flagged

    def test_flag_already_flagged(self):
        submission = self.assignment.submissions(self.active_user_ids).all()[3]
        self.assignment.flag(submission.id, self.active_user_ids)
        self.assertRaises(BadRequest, self.assignment.flag, submission.id, self.active_user_ids)

    def test_unflag_not_flagged(self):
        submission = self.assignment.submissions(self.active_user_ids).all()[3]
        self.assertRaises(BadRequest, self.assignment.unflag, submission.id, self.active_user_ids)

    def test_sabotage(self):
        submission = self.assignment.submissions([self.user1.id]).all()[3]
        self.assertRaises(BadRequest, self.assignment.flag, submission.id, [self.user2.id])

        self.assignment.flag(submission.id, [self.user1.id])
        self.assertRaises(BadRequest, self.assignment.unflag, submission.id, [self.user2.id])

    def test_accept_unflag(self):
        # when a user accepts an invitation, unflag their submissions.

        submission = self.assignment.submissions([self.user1.id]).all()[3]
        self.assignment.flag(submission.id, [self.user1.id])

        Group.invite(self.user2, self.user1, self.assignment)
        assert submission.flagged

        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user1)
        assert not submission.flagged

