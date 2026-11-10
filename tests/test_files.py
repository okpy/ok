import io
import os
import hashlib

from libcloud.storage.types import ObjectDoesNotExistError

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
                                               staff_file=True,
                                               course_id=self.course.id)
            self.blob1 = self.file1.object()


        with open(CWD + "/../server/static/img/logo.svg", 'rb') as f:
            self.file2 = ExternalFile.upload(f, name='ok.svg',
                                               user_id=self.user1.id,
                                               course_id=self.course.id,
                                               staff_file=False,
                                               assignment_id=self.assignment.id)
            self.blob2 = self.file2.object()

        db.session.add_all([self.file1, self.file2])
        db.session.commit()

    def tearDown(self):
        super().tearDown()

        delete_silently(self.blob1)
        delete_silently(self.blob2)

    def test_simple(self):
        self.assertEqual(self.blob1.driver.key, storage.driver.key)
        self.assertEqual(self.blob1.container.name, storage.container_name)
        self.assertEqual(self.blob1.container.name, self.file1.container)
        self.assertEqual(self.blob1.name, self.file1.object_name)
        blob_stream = storage.get_object_stream(self.blob1)
        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            self.assertEqual(b''.join(blob_stream), f.read())

    def test_duplicate_overwrite(self):
        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            duplicate = ExternalFile.upload(f, name='fizz.txt',
                                               user_id=self.staff1.id,
                                               course_id=self.course.id)
            duplicate_obj = duplicate.object()

        self.assertEqual(self.blob1.driver.key, duplicate_obj.driver.key)
        self.assertEqual(self.file1.filename, duplicate.filename)
        self.assertEqual(self.blob1.name, duplicate_obj.name)
        duplicate_obj.delete()

    def test_prefix(self):
        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            prefix = ExternalFile.upload(f, name='fizz.txt',
                                               user_id=self.staff1.id,
                                               prefix='test/',
                                               course_id=self.course.id)
            prefix_obj = prefix.object()

        self.assertEqual(self.blob1.driver.key, prefix_obj.driver.key)
        self.assertEqual(self.blob1.container.name, prefix.container)
        self.assertEqual(self.blob1.name, self.file1.object_name)
        self.assertEqual(prefix_obj.name, self.test_prefix_expected_obj_name)
        self.assertEqual(prefix.filename, 'fizz.txt')
        prefix_obj.delete()

    test_prefix_expected_obj_name = "test_fizz.txt"

    def test_malicious_directory_traversal(self):
        with open(CWD + "/files/fizzbuzz_after.py", 'rb') as f:
            prefix = ExternalFile.upload(f, name='fizz.txt',
                                               user_id=self.staff1.id,
                                               prefix='test/../../',
                                               course_id=self.course.id)
            prefix_obj = prefix.object()

        self.assertEqual(self.blob1.driver.key, prefix_obj.driver.key)
        self.assertEqual(self.blob1.container.name, prefix.container)
        self.assertEqual(self.blob1.name, self.file1.object_name)
        self.assertEqual(prefix_obj.name, self.test_malicious_directory_traversal_expected_obj_name)
        self.assertEqual(prefix.filename, 'fizz.txt')
        prefix_obj.delete()

    test_malicious_directory_traversal_expected_obj_name = "test_.._.._fizz.txt"

    def test_malicious_local_get_blob(self):
        with self.assertRaises(ObjectDoesNotExistError):
            blob = storage.get_blob(obj_name='../README.md')

        with self.assertRaises(ObjectDoesNotExistError):
            blob = storage.get_blob(obj_name='/bin/bash')

        with self.assertRaises(ObjectDoesNotExistError):
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
        headers, data = self.fetch_file(url)
        self.verify_download_headers(headers, self.file1.filename, "text/plain; charset=utf-8")
        self.verify_text_download(CWD + "/files/fizzbuzz_after.py", data)

    def test_api_download(self):
        self.login(self.staff1.email)
        encoded_id = utils.encode_id(self.file1.id)
        url = "/api/v3/file/{0}".format(encoded_id)
        headers, data = self.fetch_file(url)
        self.verify_download_headers(headers, self.file1.filename, "text/plain; charset=utf-8")
        self.verify_text_download(CWD + "/files/fizzbuzz_after.py", data)

    def test_binary_download(self):
        self.login(self.staff1.email)
        encoded_id = utils.encode_id(self.file2.id)
        url = "/files/{0}".format(encoded_id)
        headers, data = self.fetch_file(url)
        self.verify_download_headers(headers, self.file2.filename, "image/svg+xml")
        self.verify_binary_download(CWD + "/../server/static/img/logo.svg", data)

    def test_binary_api_download(self):
        self.login(self.staff1.email)
        encoded_id = utils.encode_id(self.file2.id)
        url = "/api/v3/file/{0}".format(encoded_id)
        self.assertEqual(self.file2.download_link, url)
        headers, data = self.fetch_file(url)
        self.verify_download_headers(headers, self.file2.filename, "image/svg+xml")
        self.verify_binary_download(CWD + "/../server/static/img/logo.svg", data)

    def test_unauth_download(self):
        self.login(self.user1.email)
        encoded_id = utils.encode_id(self.file1.id)
        url = "/files/{0}".format(encoded_id)
        response = self.client.get(url)
        self.assert404(response)

        # Should also fail via the API
        url = "/api/v3/file/{0}".format(encoded_id)
        response = self.client.get(url)
        self.assert404(response)

    def test_notfound(self):
        self.login(self.user1.email)
        encoded_id = utils.encode_id(self.file2.id * 50)

        url = "/files/{0}".format(encoded_id)
        response = self.client.get(url)
        self.assert404(response)

        # Should also fail via the API
        url = "/api/v3/file/{0}".format(encoded_id)
        response = self.client.get(url)
        self.assert404(response)

    def fetch_file(self, url):
        response = self.client.get(url)
        self.assert200(response)
        return response.headers, response.data

    def verify_download_headers(self, headers, filename, content_type):
        self.assertEqual(headers["Content-Disposition"], "attachment; filename={0!s}".format(filename))
        self.assertEqual(headers["Content-Type"], content_type)
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")

    def verify_text_download(self, file_path, downloaded_data):
        with io.open(file_path, "r", encoding="utf-8") as fobj:
            self.assertEqual(fobj.read(), downloaded_data.decode("UTF-8"))

    def verify_binary_download(self, file_path, downloaded_data):
        with open(file_path, "rb") as fobj:
            self.assertEqual(fobj.read(), downloaded_data)


def delete_silently(blob):
    try:
        blob.delete()
    except (ObjectDoesNotExistError, OSError):
        pass
