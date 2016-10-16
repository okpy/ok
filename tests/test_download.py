from tests import OkTestCase

from server.models import db, Assignment, Backup, Message, User
from server import utils

class TestDownload(OkTestCase):
    def _add_file(self, filename, contents):
        self.setup_course()

        email = 'student1@okpy.org'
        self.login(email)
        self.user = User.lookup(email)

        self.backup = Backup(
            submitter=self.user,
            assignment=self.assignment,
            submit=True)

        self.message = Message(
            backup=self.backup,
            contents={
                filename: contents,
                'submit': True
            },
            kind='file_contents')

        db.session.add(self.backup)
        db.session.add(self.message)
        db.session.commit()

    def test_simple(self):
        filename = "test.py"
        contents = "x = 4"
        self._add_file(filename, contents)
        encoded_id = utils.encode_id(self.backup.id)
        submit_str = "submissions" if self.backup.submit else "backups"
        url = "/{0}/{1}/{2}/download/{3}".format(self.assignment.name, submit_str, encoded_id, filename)
        response = self.client.get(url)
        self.assert_200(response)
        self.assertEqual(contents, response.data.decode('UTF-8'))

    def test_incorrect_hash(self):
        filename = "test.py"
        contents = "x = 4"
        self._add_file(filename, contents)
        encoded_id = utils.encode_id(self.backup.id)
        submit_str = "submissions" if self.backup.submit else "backups"
        url = "/{0}/{1}/{2}/download/{3}".format(self.assignment.name, submit_str, "xxxxx", filename)
        response = self.client.get(url)
        self.assert_404(response)
        url = "/{0}/{1}/{2}/download/{3}".format(self.assignment.name, submit_str, "123", filename)
        response = self.client.get(url)
        self.assert_404(response)

    def test_incorrect_submit_boolean(self):
        filename = "test.py"
        contents = "x = 4"
        self._add_file(filename, contents)
        encoded_id = utils.encode_id(self.backup.id)
        wrong_submit_str = "backups" if self.backup.submit else "submissions" # intentionally flipped
        correct_submit_str = "submissions" if self.backup.submit else "backups"
        url = "/{0}/{1}/{2}/download/{3}"
        wrong_url = url.format(self.assignment.name, wrong_submit_str, encoded_id, filename)
        redir_url = url.format(self.assignment.name, correct_submit_str, encoded_id, filename)
        response = self.client.get(wrong_url)
        self.assertRedirects(response, redir_url)
        response = self.client.get(redir_url)
        self.assertEqual(contents, response.data.decode('UTF-8'))

    def test_unicode(self):
        filename = "test.py"
        contents = "⚡️ 🔥 💥 ❄️"
        self._add_file(filename, contents)
        encoded_id = utils.encode_id(self.backup.id)
        submit_str = "submissions" if self.backup.submit else "backups"
        url = "/{0}/{1}/{2}/download/{3}".format(self.assignment.name, submit_str, encoded_id, filename)
        response = self.client.get(url)
        self.assert_200(response)
        self.assertEqual(contents, response.data.decode('UTF-8'))

    def test_folders(self):
        filename = "tests/hof.py"
        contents = "tests = {\nstatus: 'locked'\n}"
        self._add_file(filename, contents)
        encoded_id = utils.encode_id(self.backup.id)
        submit_str = "submissions" if self.backup.submit else "backups"
        url = "/{0}/{1}/{2}/download/{3}".format(self.assignment.name, submit_str, encoded_id, filename)
        response = self.client.get(url)
        self.assert_200(response)
        self.assertEqual(contents, response.data.decode('UTF-8'))

    def test_wrong_student(self):
        filename = "test.py"
        contents = "x = 4"
        self._add_file(filename, contents)
        self.login('student2@okpy.org')
        encoded_id = utils.encode_id(self.backup.id)
        submit_str = "submissions" if self.backup.submit else "backups"
        url = "/{0}/{1}/{2}/download/{3}".format(self.assignment.name, submit_str, encoded_id, filename)
        response = self.client.get(url)
        self.assert_404(response)

    def test_staff(self):
        filename = "test.py"
        contents = "x = 4"
        self._add_file(filename, contents)
        self.login(self.staff1.email)

        encoded_id = utils.encode_id(self.backup.id)
        submit_str = "submissions" if self.backup.submit else "backups"
        url = "/{0}/{1}/{2}/download/{3}".format(self.assignment.name, submit_str, encoded_id, filename)
        response = self.client.get(url)
        self.assert_200(response)
