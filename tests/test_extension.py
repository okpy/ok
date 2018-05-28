import datetime as dt
import json

from server.models import db, Backup, Group, Extension
from server.controllers import api

from tests import OkTestCase

class TestExtension(OkTestCase):
    """Tests the creation of extensions & submissions."""
    def setUp(self):
        super(TestExtension, self).setUp()
        self.setup_course()

    def set_offset(self, offset):
        self.assignment.due_date = self.assignment.due_date + dt.timedelta(hours=offset)
        self.assignment.lock_date = self.assignment.lock_date + dt.timedelta(days=offset)

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
        custom_time = custom_time or dt.datetime.utcnow()
        return Extension.create(assignment=assignment, user=user,
                custom_submission_time=custom_time,
                expires=dt.datetime.utcnow() + dt.timedelta(days=1),
                staff=self.staff1)

    def test_extension_basic(self):
        ext = self._make_ext(self.assignment, self.user1)
        self.assertEqual(ext, Extension.get_extension(self.user1, self.assignment))
        self.assertFalse(Extension.get_extension(self.user2, self.assignment))

    def test_extension_permissions(self):
        ext = self._make_ext(self.assignment, self.user1)
        self.assertFalse(Extension.can(ext, self.user1, 'delete'))
        self.assertTrue(Extension.can(ext, self.staff1, 'delete'))

    def test_extension_expiry(self):
        ext = self._make_ext(self.assignment, self.user1)
        self.assertEqual(ext, Extension.get_extension(self.user1, self.assignment))
        ext.expires = dt.datetime.utcnow() - dt.timedelta(days=1)
        self.assertFalse(Extension.get_extension(self.user1, self.assignment))

    def test_extension_group(self):
        self.set_offset(1) # Allow assignment to be active
        Group.invite(self.user1, self.user2, self.assignment)
        Group.invite(self.user1, self.user3, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)
        self.set_offset(-2) # Lock assignment

        ext = self._make_ext(self.assignment, self.user1)
        self.assertEqual(ext, Extension.get_extension(self.user1, self.assignment))
        self.assertEqual(ext, Extension.get_extension(self.user2, self.assignment))
        # User 3 has not accepted yet so does not get an extension
        self.assertFalse(Extension.get_extension(self.user3, self.assignment))

        # If user 2 leaves, they no longer have access to the extension
        self.set_offset(1) # Allow assignment to be active to remove the user.
        group.remove(self.user1, self.user2)
        self.assertFalse(Extension.get_extension(self.user2, self.assignment))

    def test_submit_with_extension(self):
        self.set_offset(-2) # Lock assignment
        # Should fail because it's late.
        self._submit_to_api(self.user1, False)
        num_backups = Backup.query.filter(Backup.submitter_id == self.user1.id).count()
        self.assertEqual(num_backups, 1) # Failed submissions are still collected.

        ext = self._make_ext(self.assignment, self.user1)
        # Should allow submission after the submission
        self._submit_to_api(self.user1, True)

        # The custom_submission_time should always be set for extensions
        backup = Backup.query.filter(Backup.submitter_id == self.user1.id,
                                     Backup.submit == True).first()
        self.assertIsNotNone(backup)
        self.assertEqual(backup.custom_submission_time, ext.custom_submission_time)

        # Others should still not be able to submit
        self._submit_to_api(self.user2, False)

    def test_submit_with_extension_while_active(self):
        self.set_offset(1) # Activate assignment

        # Extensions should have no effect
        self._submit_to_api(self.user1, True)
        ext = self._make_ext(self.assignment, self.user1)
        # Should allow submission after the submission
        self._submit_to_api(self.user1, True)

        # The custom_submission_time should always be set for extensions
        backup = Backup.query.filter(Backup.submitter_id == self.user1.id,
                                     Backup.submit == True).first()
        self.assertIsNotNone(backup)
        self.assertEqual(backup.custom_submission_time,
                             ext.custom_submission_time)

    def test_group_submit_with_extension(self):
        self.set_offset(-2) # Lock assignment

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
        self.set_offset(-2) # Lock assignment
        self._submit_to_api(self.user1, False)

        ext = self._make_ext(self.assignment, self.user1)
        # Should allow submission after the submission
        self._submit_to_api(self.user1, True)
        ext.expires = dt.datetime.utcnow() - dt.timedelta(days=1)
        # But not after the extension has expired
        self._submit_to_api(self.user1, False)

    def test_submit_between_due_and_lock(self):
        """ Extensions should also change the custom submission time
        when submitted after the due date but before the lock date.
        """
        self.assignment.due_date = dt.datetime.utcnow() + dt.timedelta(hours=-1)
        self.assignment.lock_date = dt.datetime.utcnow() + dt.timedelta(hours=1)

        Group.force_add(self.staff1, self.user1, self.user2, self.assignment)

        # User 1 is allowed to submit since it's between due and lock date
        self._submit_to_api(self.user1, True)
        first_back = Backup.query.filter(Backup.submitter_id == self.user1.id,
                                         Backup.submit == True).first()
        self.assertIsNone(first_back.custom_submission_time)
        ext = self._make_ext(self.assignment, self.user1)
        self._submit_to_api(self.user2, True)

        second_back = Backup.query.filter(Backup.submitter_id == self.user2.id,
                                          Backup.submit == True).first()
        # The submission from User 2 should have a custom submission time
        self.assertEqual(second_back.custom_submission_time, ext.custom_submission_time)

    def test_extension_after_backups(self):
        """ Backups from before the extension was made should use the extension
        time instead of the submission time.
        """
        now = dt.datetime.utcnow()
        self.assignment.due_date = now - dt.timedelta(hours=1)

        # Make a late backup
        backup = api.make_backup(self.user1, self.assignment.id, messages={}, submit=True)
        self.assertFalse(backup.submission_time <= self.assignment.due_date)

        # After an extension, backup should no longer be late
        early = now - dt.timedelta(days=1)
        ext = self._make_ext(self.assignment, self.user1, custom_time=early)
        self.assertTrue(backup.submission_time <= self.assignment.due_date)
