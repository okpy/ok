import datetime
import json

from werkzeug.exceptions import BadRequest

from server.models import db, Backup, Group, Message, Version, Score

from tests import OkTestCase

class TestRevision(OkTestCase):
    """Tests revision API submission and scoring."""
    def setUp(self):
        """ Add submissions for 3 users. """
        super(TestRevision, self).setUp()
        self.setup_course()

        message_dict = {'file_contents': {'backup.py': '1'}, 'analytics': {}}

        self.active_user_ids = [self.user1.id, self.user2.id, self.user3.id]

        self.assignment.revisions_allowed = True

        time = self.assignment.due_date # Set to dt.now(), so future subms are late
        for user_id in self.active_user_ids:
            time -= datetime.timedelta(minutes=15)
            backup = Backup(submitter_id=user_id,
                            assignment=self.assignment, submit=True)
            # Revisions are submitted on time.
            backup.created = time
            messages = [Message(kind=k, backup=backup,
                                contents=m) for k, m in message_dict.items()]
            db.session.add_all(messages)
            db.session.add(backup)

        # Put user 3 in a group with user 4
        Group.invite(self.user3, self.user4, self.assignment)
        group = Group.lookup(self.user3, self.assignment)
        group.accept(self.user4)

        okversion = Version(name="ok-client", current_version="v1.5.0",
            download_link="http://localhost/ok")
        db.session.add(okversion)

        db.session.commit()


    def _submit_revision(self):
        data = {
            'assignment': self.assignment.name,
            'messages': {
                'file_contents': {
                    'hog.py': 'print("Hello world!")'
                }
            },
            'submit': False,
            'revision': True,
        }

        response = self.client.post('/api/v3/revision/?client_version=v1.5.0',
            data=json.dumps(data),
            headers=[('Content-Type', 'application/json')])
        return response

    def test_no_revisions(self):
        """ Ensure no user has revisions before submitting ."""
        for user in self.active_user_ids:
            revision = self.assignment.revision({self.user1.id})
            self.assertIs(revision, None)

    def test_revison_anon(self):
        response = self._submit_revision()
        self.assert401(response)

    def test_revison_submit(self):
        self.login(self.user1.email)
        response = self._submit_revision()
        self.assert200(response)

        revision = self.assignment.revision({self.user1.id})
        self.assertTrue(revision.is_revision)

    def test_revison_disabled(self):
        # Disable revisions
        self.assignment.revisions_allowed = False
        db.session.commit()

        self.login(self.user1.email)
        response = self._submit_revision()
        self.assert403(response)

        # Ensure that the backup is still accepted
        backups = Backup.query.filter_by(submitter=self.user1).count()
        self.assertEquals(backups, 2)

    def test_revison_no_submission(self):
        """ Revisions are not accepted if there is no final submission. """
        self.login(self.user5.email)
        response = self._submit_revision()
        self.assert403(response)

        # Ensure that the backup is still accepted
        backups = Backup.query.filter_by(submitter=self.user5).count()
        self.assertEquals(backups, 1)

    def test_revison_test_group_member(self):
        self.login(self.user4.email)
        response = self._submit_revision()
        self.assert200(response)

        group = self.assignment.active_user_ids(self.user4.id)
        revision = self.assignment.revision(group)
        self.assertEquals(len(revision.owners()), 2)

    def test_revison_multiple_submit(self):
        group = self.assignment.active_user_ids(self.user3.id)

        self.login(self.user3.email)
        response = self._submit_revision()
        self.assert200(response)

        first_revision = self.assignment.revision(group)
        self.assertTrue(first_revision.is_revision)

        self.login(self.user4.email)
        response = self._submit_revision()
        self.assert200(response)

        second_revision = self.assignment.revision(group)
        self.assertTrue(second_revision.is_revision)
        self.assertNotEquals(first_revision.id, second_revision.id)

        # Check the number of revisions scores is 1
        scores = Score.query.filter_by(kind="revision", archived=False).count()
        self.assertEquals(scores, 1)
