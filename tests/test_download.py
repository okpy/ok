from .helpers import OkTestCase

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
            assignment=self.assignment)
            
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
        url = '/download/%s/%s' % (utils.encode_id(self.backup.id), filename)
        response = self.client.get(url)
        self.assert_200(response)
        self.assertEqual(contents, response.data.decode('UTF-8'))
        
    def test_unicode(self):
        filename = "test.py"
        contents = "⚡️ 🔥 💥 ❄️"
        self._add_file(filename, contents)
        url = '/download/%s/%s' % (utils.encode_id(self.backup.id), filename)
        response = self.client.get(url)
        self.assert_200(response)
        self.assertEqual(contents, response.data.decode('UTF-8'))
        
    def test_wrong_student(self):
        filename = "test.py"
        contents = "x = 4"
        self._add_file(filename, contents)
        self.login('student2@okpy.org')
        url = '/download/%s/%s' % (utils.encode_id(self.backup.id), filename)
        response = self.client.get(url)
        self.assert_404(response)
