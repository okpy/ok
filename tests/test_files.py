import os
import hashlib

from tests import OkTestCase

from server.models import db, Group, Course, ExternalFile, User
from server.extensions import storage

from server import utils

CWD = os.path.dirname(__file__)

class TestFile(OkTestCase):
    def setUp(self):
        super(TestFile, self).setUp()
        self.setup_course()

        self.upload1 = utils.upload_file(CWD + "/files/fizzbuzz_after.py", name='fizz.txt')
        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            self.fizz_contents = f.read().decode('UTF-8')

        self.file1 = ExternalFile(
            container=self.upload1.container.driver.key,
            filename='fizz.txt',
            object_name=self.upload1.name,
            course_id=self.course.id,
            user_id=self.staff1.id,
            is_staff=True)

        self.upload2 = utils.upload_file(CWD + "/../server/static/img/logo.svg", name='ok.svg')

        self.file2 = ExternalFile(
            container=self.upload2.container.driver.key,
            filename='ok.svg',
            object_name=self.upload2.name,
            course_id=self.course.id,
            assignment_id=self.assignment.id,
            user_id=self.user1.id,
            is_staff=False)

        db.session.add_all([self.file1, self.file2])
        db.session.commit()

    def teardown_method(self, test_method):
        self.upload1.delete()
        self.upload2.delete()

    def test_simple(self):
        file_obj = self.file1.object
        self.assertEquals(file_obj.driver.key, self.file1.container)
        self.assertEquals(file_obj.name, self.file1.object_name)
        self.assertEquals(file_obj.hash, self.upload1.hash)

    def test_duplicate(self):
        file_obj = self.file1.object
        duplicate_obj = utils.upload_file(CWD + "/files/fizzbuzz_after.py", name='fizz.txt')
        self.assertEquals(file_obj.driver.key, duplicate_obj.driver.key)
        self.assertNotEquals(file_obj.name, duplicate_obj.name)
        duplicate_obj.delete()

    def test_prefix(self):
        file_obj = self.file1.object
        prefix_obj = utils.upload_file(CWD + "/files/fizzbuzz_after.py", name='fizz.txt', prefix='test/')
        self.assertEquals(file_obj.driver.key, prefix_obj.driver.key)
        self.assertEquals(file_obj.name, self.file1.object_name)
        self.assertEquals(prefix_obj.name, 'test/fizz.txt')
        prefix_obj.delete()

    def test_permission(self):
        # Students can not access files of staff
        self.assertTrue(ExternalFile.can(self.file1, self.staff1, 'download'))
        self.assertFalse(ExternalFile.can(self.file1, self.user1, 'download'))
        self.assertFalse(ExternalFile.can(self.file1, self.lab_assistant1, 'download'))

        # Staff and student can access student files
        self.assertTrue(ExternalFile.can(self.file2, self.user1, 'download'))
        self.assertTrue(ExternalFile.can(self.file2, self.staff1, 'download'))
        self.assertFalse(ExternalFile.can(self.file2, self.user2, 'download'))

    def test_group_permission(self):
        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)

        # Only the original creator and staff can accept the files
        self.assertTrue(ExternalFile.can(self.file2, self.user1, 'download'))
        self.assertTrue(ExternalFile.can(self.file2, self.staff1, 'download'))
        self.assertFalse(ExternalFile.can(self.file2, self.user2, 'download'))

        group.accept(self.user2)

        # Now all group members can access the files
        self.assertTrue(ExternalFile.can(self.file2, self.user1, 'download'))
        self.assertTrue(ExternalFile.can(self.file2, self.staff1, 'download'))
        self.assertTrue(ExternalFile.can(self.file2, self.user2, 'download'))
        self.assertFalse(ExternalFile.can(self.file2, self.user3, 'download'))

    def test_delete(self):
        """ Students should not be able to delete files. A deletion should work.
        """
        self.assertFalse(ExternalFile.can(self.file1, self.user1, 'delete'))
        self.assertTrue(ExternalFile.can(self.file1, self.staff1, 'delete'))
        self.file1.delete()
        self.assertTrue(self.file1.deleted)

    def test_web_download(self):
        self.login(self.staff1.email)
        encoded_id = utils.encode_id(self.file1.id)
        url = "/files/{0}".format(encoded_id)
        redirect_url = "/files/{0}/download".format(encoded_id)
        response = self.client.get(url)
        self.assertRedirects(response, redirect_url)
        download = self.client.get(redirect_url)

        self.assertEquals("attachment; filename={0!s}".format(self.file1.filename),
                          download.headers.get('Content-Disposition'))
        self.assertEquals(download.headers['Content-Type'], 'text/plain; charset=utf-8')
        self.assertEquals(download.headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.fizz_contents, download.data.decode('UTF-8'))


    def test_binary_download(self):
        self.login(self.staff1.email)
        encoded_id = utils.encode_id(self.file2.id)
        url = "/files/{0}".format(encoded_id)
        redirect_url = "/files/{0}/download".format(encoded_id)
        response = self.client.get(url)
        self.assertRedirects(response, redirect_url)
        download = self.client.get(redirect_url)
        self.assertEquals("attachment; filename={0!s}".format(self.file2.filename),
                          download.headers.get('Content-Disposition'))
        self.assertEquals(download.headers['Content-Type'], 'image/svg+xml')
        self.assertEquals(download.headers['X-Content-Type-Options'], 'nosniff')

    def test_unauth_download(self):
        self.login(self.user1.email)
        encoded_id = utils.encode_id(self.file1.id)
        url = "/files/{0}".format(encoded_id)
        response = self.client.get(url)
        self.assert404(response)

    def test_notfound(self):
        self.login(self.user1.email)
        encoded_id = utils.encode_id(self.file2.id * 50)
        url = "/files/{0}".format(encoded_id)
        response = self.client.get(url)
        self.assert404(response)
