import os
import hashlib

from libcloud.storage.types import ObjectDoesNotExistError
import pytest

from tests import OkTestCase

from server.models import db, Group, Course, ExternalFile, User
from server.extensions import storage

from server import utils

CWD = os.path.dirname(__file__)

class TestFile(OkTestCase):
    def setUp(self):
        super(TestFile, self).setUp()
        self.setup_course()

        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            self.file1 = ExternalFile.upload(f, name='fizz.txt',
                                               user_id=self.staff1.id,
                                               course_id=self.course.id)
            self.blob1 = self.file1.object()


        with open(CWD + "/../server/static/img/logo.svg", 'rb') as f:
            self.file2 = ExternalFile.upload(f, name='ok.svg',
                                               user_id=self.user1.id,
                                               course_id=self.course.id,
                                               assignment_id=self.assignment.id)
            self.blob2 = self.file1.object()

        db.session.add_all([self.file1, self.file2])
        db.session.commit()

    def teardown_method(self, test_method):
        self.blob1.delete()
        self.blob2.delete()

    def test_simple(self):
        self.assertEquals(self.blob1.driver.key, storage.driver.key)
        self.assertEquals(self.blob1.container.name, storage.container_name)
        self.assertEquals(self.blob1.container.name, self.file1.container)
        self.assertEquals(self.blob1.name, self.file1.object_name)
        blob_stream = storage.get_object_stream(self.blob1)
        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            self.assertEquals(b''.join(blob_stream), f.read())

    def test_duplicate_overwrite(self):
        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            duplicate = ExternalFile.upload(f, name='fizz.txt',
                                               user_id=self.staff1.id,
                                               course_id=self.course.id)
            duplicate_obj = duplicate.object()

        self.assertEquals(self.blob1.driver.key, duplicate_obj.driver.key)
        self.assertEquals(self.file1.filename, duplicate.filename)
        self.assertEquals(self.blob1.name, duplicate_obj.name)
        duplicate_obj.delete()

    def test_prefix(self):
        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            prefix = ExternalFile.upload(f, name='fizz.txt',
                                               user_id=self.staff1.id,
                                               prefix='test/',
                                               course_id=self.course.id)
            prefix_obj = prefix.object()

        self.assertEquals(self.blob1.driver.key, prefix_obj.driver.key)
        self.assertEquals(self.blob1.container.name, prefix.container)
        self.assertEquals(self.blob1.name, self.file1.object_name)
        self.assertEquals(prefix_obj.name, 'test_fizz.txt')
        self.assertEquals(prefix.filename, 'fizz.txt')
        prefix_obj.delete()

    def test_malicious_directory_traversal(self):
        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            prefix = ExternalFile.upload(f, name='fizz.txt',
                                               user_id=self.staff1.id,
                                               prefix='test/../../',
                                               course_id=self.course.id)
            prefix_obj = prefix.object()

        self.assertEquals(self.blob1.driver.key, prefix_obj.driver.key)
        self.assertEquals(self.blob1.container.name, prefix.container)
        self.assertEquals(self.blob1.name, self.file1.object_name)
        self.assertEquals(prefix_obj.name, 'test_.._.._fizz.txt')
        self.assertEquals(prefix.filename, 'fizz.txt')
        prefix_obj.delete()

    def test_malicious_local_get_blob(self):
        with pytest.raises(ObjectDoesNotExistError):
            blob = storage.get_blob(obj_name='../README.md')

        with pytest.raises(ObjectDoesNotExistError):
            blob = storage.get_blob(obj_name='/bin/bash')

        with pytest.raises(ObjectDoesNotExistError):
            blob = storage.get_blob(obj_name='foobar.txt')

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
        response = self.client.get(url)
        self.assert200(response)
        self.assertEquals("attachment; filename={0!s}".format(self.file1.filename),
                          response.headers.get('Content-Disposition'))
        self.assertEquals(response.headers['Content-Type'], 'text/plain; charset=utf-8')
        self.assertEquals(response.headers['X-Content-Type-Options'], 'nosniff')
        with open(CWD + "/files/fizzbuzz_after.py", 'r') as f:
            self.assertEqual(f.read(), response.data.decode('UTF-8'))

    def test_binary_download(self):
        self.login(self.staff1.email)
        encoded_id = utils.encode_id(self.file2.id)
        url = "/files/{0}".format(encoded_id)
        response = self.client.get(url)
        self.assert200(response)
        self.assertEquals("attachment; filename={0!s}".format(self.file2.filename),
                          response.headers.get('Content-Disposition'))
        self.assertEquals(response.headers['Content-Type'], 'image/svg+xml')
        self.assertEquals(response.headers['X-Content-Type-Options'], 'nosniff')

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
