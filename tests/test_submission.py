import datetime
from werkzeug.exceptions import BadRequest

from server.models import db, Backup, Group, Message

from tests import OkTestCase

class TestSubmission(OkTestCase):
    """Tests flagging submissions and final submissions."""
    def setUp(self):
        super(TestSubmission, self).setUp()
        self.setup_course()
        self.active_user_ids = [self.user1.id, self.user2.id, self.user3.id]
        self._make_assignment(self.active_user_ids, self.assignment)

    def _make_assignment(self, uids, assignment):
        # create a submission every 15 minutes
        message_dict = {'file_contents': {'backup.py': '1'}, 'analytics': {}}
        time = assignment.due_date
        for _ in range(20):
            for user_id in uids:
                time -= datetime.timedelta(minutes=15)
                backup = Backup(submitter_id=user_id,
                    assignment=assignment, submit=True)
                messages = [Message(kind=k, backup=backup,
                    contents=m) for k, m in message_dict.items()]
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

    def test_two_assignments(self):
        submission1 = self.assignment.submissions(self.active_user_ids).all()[3]
        submission2 = self.assignment.submissions(self.active_user_ids).all()[7]
        self.assignment.flag(submission1.id, self.active_user_ids)
        self.assignment.flag(submission2.id, self.active_user_ids)

        final = self.assignment.final_submission(self.active_user_ids)
        assert final == submission2
        assert not submission1.flagged

        new_assignment = self.assignment2
        self._make_assignment(self.active_user_ids, self.assignment2)

        secondary_submit = self.assignment2.submissions(self.active_user_ids).all()[3]
        secondary_final = self.assignment2.final_submission(self.active_user_ids)

        # Final submission should be specific to assignments
        assert final != secondary_final
        # 4th most recent submit should not be final
        assert secondary_submit != secondary_final
        assert not secondary_final.flagged

        self.assignment2.flag(secondary_submit.id, self.active_user_ids)
        new_secondary_final = self.assignment2.final_submission(self.active_user_ids)
        # Flagged submission should be recognized as the final.
        assert secondary_submit == new_secondary_final
        assert secondary_final.flagged

        # It should not affect the final submission of the other assignment
        a1_final = self.assignment.final_submission(self.active_user_ids)
        assert final == a1_final
        assert final == submission2


    def test_unflag(self):
        submission = self.assignment.submissions(self.active_user_ids).all()[3]
        self.assignment.flag(submission.id, self.active_user_ids)
        self.assignment.unflag(submission.id, self.active_user_ids)

        final = self.assignment.final_submission(self.active_user_ids)
        most_recent = self.assignment.submissions(self.active_user_ids).first()
        assert final == most_recent
        assert not submission.flagged

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

    def test_files(self):
        backup = Backup(
            submitter_id=self.user1.id,
            assignment=self.assignment,
            submit=True)
        message = Message(
            kind='file_contents',
            backup=backup,
            contents={
                'hog.py': 'def foo():\n    return',
                'submit': True
            })
        db.session.add(message)
        db.session.add(backup)
        db.session.commit()

        # submit should not show up
        assert backup.files() == {
            'hog.py': 'def foo():\n    return'
        }

    def test_backup_owners(self):
        backup = Backup(
            submitter_id=self.user1.id,
            assignment=self.assignment,
            submit=True)
        backup2 = Backup(
            submitter_id=self.user2.id,
            assignment=self.assignment,
            submit=True)
        db.session.add(backup)
        db.session.add(backup2)
        db.session.commit()
        assert backup2.owners() == {self.user2.id}

        Group.invite(self.user1, self.user2, self.assignment)
        Group.invite(self.user1, self.user3, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        assert backup.owners() == {self.user1.id, self.user2.id}
        assert backup2.owners() == {self.user1.id, self.user2.id}
