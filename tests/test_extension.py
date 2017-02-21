import datetime as dt
import json

from server.models import db, Backup, Group, Extension

from tests import OkTestCase

class TestExtension(OkTestCase):
    """Tests the creation of extensions & submissions."""
    def setUp(self):
        super(TestExtension, self).setUp()
        self.setup_course()

    def set_offset(self, offset):
        self.assignment.due_date = self.assignment.due_date + dt.timedelta(hours=offset)
        self.assignment.lock_date = self.assignment.lock_date + dt.timedelta(days=offset)
        db.session.commit()

    def _submit_to_api(self, user, success):
        self.login(user.email)
        data = {
            'assignment': self.assignment.name,
            'messages': {
                'file_contents': {
                    'hog.py': 'print("Hello world!")'
                }
            },
            'submit': True,
        }

        response = self.client.post('/api/v3/backups/?client_version=v1.5.0',
            data=json.dumps(data),
            headers=[('Content-Type', 'application/json')])
        if success:
            self.assert_200(response)
            assert 'email' in response.json['data']
        else:
            self.assert_403(response)
            assert response.json['data'] == {
                'data': {
                    'backup': True,
                    'late': True
                }
            }


    def _make_ext(self, assignment, user, custom_time=None):
        if not custom_time:
           custom_time = dt.datetime.utcnow()

        ext = Extension(assignment=assignment, user=user,
                              custom_submission_time=custom_time,
                              expires=dt.datetime.utcnow() + dt.timedelta(days=1),
                              message='They are good students Brent!',
                              creator=self.staff1)
        db.session.add(ext)
        db.session.commit()
        return ext

    def test_extension_basic(self):
        ext = self._make_ext(self.assignment, self.user1)
        self.assertEquals(ext, Extension.get_extension(self.user1, self.assignment))
        self.assertFalse(Extension.get_extension(self.user2, self.assignment))

    def test_extension_expiry(self):
        ext = self._make_ext(self.assignment, self.user1)
        self.assertEquals(ext, Extension.get_extension(self.user1, self.assignment))
        ext.expires = dt.datetime.utcnow() - dt.timedelta(days=1)
        self.assertFalse(Extension.get_extension(self.user1, self.assignment))

    def test_extension_group(self):
        self.set_offset(1) # Allow assignment to be active
        Group.invite(self.user1, self.user2, self.assignment)
        Group.invite(self.user1, self.user3, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)
        self.set_offset(-1) # Lock assignment

        ext = self._make_ext(self.assignment, self.user1)
        self.assertEquals(ext, Extension.get_extension(self.user1, self.assignment))
        self.assertEquals(ext, Extension.get_extension(self.user2, self.assignment))
        # User 3 has not accepted yet so does not get an extension
        self.assertFalse(Extension.get_extension(self.user3, self.assignment))

        # If user 2 leaves, they no longer have access to the extension
        group.remove(self.user1, self.user2)
        self.assertFalse(Extension.get_extension(self.user2, self.assignment))

    def test_submit_with_extension(self):
        self.set_offset(-1) # Lock assignment
        # Should fail because it's late.
        self._submit_to_api(self.user1, False)
        num_backups = Backup.query.filter(Backup.submitter_id == self.user1.id).count()
        self.assertEquals(num_backups, 1) # Failed submissions are still collected.

        ext = self._make_ext(self.assignment, self.user1)
        # Should allow submission after the submission
        self._submit_to_api(self.user1, True)

        # The custom_submission_time should be set
        backup = Backup.query.filter(Backup.submitter_id == self.user1.id,
                                     Backup.submit == True).first()
        self.assertIsNotNone(backup)
        self.assertEquals(backup.custom_submission_time, ext.custom_submission_time)

        # Others should still not be able to submit
        self._submit_to_api(self.user2, False)

    def test_submit_with_extension_while_active(self):
        self.set_offset(1) # Activate assignment

        # Extensions should have no effect
        self._submit_to_api(self.user1, True)
        ext = self._make_ext(self.assignment, self.user1)
        # Should allow submission after the submission
        self._submit_to_api(self.user1, True)

        # The custom_submission_time should not be set
        backup = Backup.query.filter(Backup.submitter_id == self.user1.id,
                                     Backup.submit == True).first()
        self.assertIsNotNone(backup)
        self.assertNotEquals(backup.custom_submission_time,
                             ext.custom_submission_time)

    def test_group_submit_with_extension(self):
        self.set_offset(-1) # Lock assignment

        # Should fail because it's late.
        self._submit_to_api(self.user2, False)

        Group.force_add(self.staff1, self.user1, self.user2, self.assignment)
        ext = self._make_ext(self.assignment, self.user1)

        # An extension for user1 should also apply to all members of the group
        self._submit_to_api(self.user2, True)
        self._submit_to_api(self.user1, True)
        self._submit_to_api(self.user3, False)

        Group.force_add(self.staff1, self.user1, self.user3, self.assignment)
        self._submit_to_api(self.user3, True)

    def test_submit_with_expired_extension(self):
        self.set_offset(-1) # Lock assignment
        self._submit_to_api(self.user1, False)

        ext = self._make_ext(self.assignment, self.user1)
        # Should allow submission after the submission
        self._submit_to_api(self.user1, True)
        ext.expires = dt.datetime.utcnow() - dt.timedelta(days=1)
        # But not after the extension has expired
        self._submit_to_api(self.user1, False)
