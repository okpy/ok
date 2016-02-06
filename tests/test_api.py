import datetime
import json
from server.models import db, Assignment, Backup, Course, User, Version
from server.utils import encode_id

from tests import OkTestCase

class TestAuth(OkTestCase):
    def _test_backup(self, submit):
        email = 'student@okpy.org'
        self.login(email)
        user = User.lookup(email)

        course = Course(offering='cal/cs61a/sp16')
        assignment = Assignment(
            name='cal/cs61a/sp16/proj1',
            course=course,
            display_name='Hog',
            due_date=datetime.datetime.now(),
            lock_date=datetime.datetime.now() + datetime.timedelta(days=1),
            max_group_size=4)
        db.session.add(assignment)
        db.session.commit()

        okversion = Version(name="ok", current_version="v1.5.0",
            download_link="http://localhost/ok")
        db.session.add(okversion)

        data = {
            'assignment': assignment.name,
            'messages': {
                'file_contents': {
                    'hog.py': 'print("Hello world!")'
                }
            },
            'submit': submit,
        }

        response = self.client.post('/api/v3/backups/?client_version=v1.4.0',
            data=json.dumps(data),
            headers=[('Content-Type', 'application/json')])
        self.assert_403(response)
        assert response.json['data'] == {
            'supplied': 'v1.4.0',
            'correct': 'v1.5.0',
            'download_link': "http://localhost/ok"
        }
        assert 'Incorrect client version' in response.json['message']
        backup = Backup.query.filter(Backup.submitter_id == user.id).all()
        assert backup == []

        response = self.client.post('/api/v3/backups/?client_version=v1.5.0',
            data=json.dumps(data),
            headers=[('Content-Type', 'application/json')])
        backup = Backup.query.filter(Backup.submitter_id == user.id).first()
        assert backup is not None

        self.assert_200(response)
        assert response.json['data'] == {
            'email': email,
            'key': encode_id(backup.id),
            'course': {
                'id': course.id,
                'offering': course.offering,
                'display_name': course.display_name,
                'active': course.active
            },
            'assignment': assignment.name
        }

        assert backup.assignment == assignment
        assert backup.submitter_id == user.id
        assert len(backup.messages) == len(data['messages'])
        assert backup.submit == submit

    def test_backup(self):
        self._test_backup(False)

    def test_submit(self):
        self._test_backup(True)

    def test_api(self):
        response = self.client.get('/api/v3/')
        self.assert_200(response)
        assert response.json['data'] == {
            'version': 'v3',
            'url': '/api/v3/',
            'documentation': 'http://github.com/Cal-CS-61A-Staff/ok/wiki'
        }
        assert response.json['message'] == 'success'
        assert response.json['code'] == 200

    def test_non_existant_api(self):
        response = self.client.get('/api/v3/doesnotexist')
        self.assert_404(response)
        assert response.json['data'] == {}
        assert response.json['code'] == 404

    def test_version_api(self):
        okversion = Version(name="ok", current_version="v1.5.0",
            download_link="http://localhost/ok")
        db.session.add(okversion)
        ok2version = Version(name="ok2", current_version="v2.5.0",
            download_link="http://localhost/ok2")
        db.session.add(ok2version)

        response = self.client.get('/api/v3/version/')
        self.assert_200(response)
        assert response.json['data'] == {
            'results': [
                {
                    "current_version": "v1.5.0",
                    "download_link": "http://localhost/ok",
                    "name": "ok"
                },
                {
                    "current_version": "v2.5.0",
                    "download_link": "http://localhost/ok2",
                    "name": "ok2"
                }
            ]
        }
        assert response.json['message'] == 'success'

        response = self.client.get('/api/v3/version/ok')
        self.assert_200(response)
        assert response.json['data'] == {
            'results': [
                {
                    "current_version": "v1.5.0",
                    "download_link": "http://localhost/ok",
                    "name": "ok"
                }
            ]
        }
