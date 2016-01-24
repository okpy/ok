import datetime
import json
from server.models import db, Assignment, Backup, Course, User

from .helpers import OkTestCase

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

        data = {
            'assignment': assignment.name,
            'messages': {
                'file_contents': {
                    'hog.py': 'print "Hello world!"'
                }
            },
            'submit': submit
        }

        response = self.client.post('/api/v3/backups/', data=json.dumps(data),
            headers=[('Content-Type', 'application/json')])
        backup = Backup.query.filter(Backup.submitter_id == user.id).first()
        assert backup is not None

        self.assert_200(response)
        assert response.json['data'] == {
            'email': email,
            'key': backup.id,
            'course': course.id,
            'assignment': assignment.id
        }

        assert backup.assignment == assignment
        assert backup.submitter_id == user.id
        assert len(backup.messages) == len(data['messages'])
        assert backup.submit == submit

    def test_backup(self):
        self._test_backup(False)

    def test_submit(self):
        self._test_backup(True)
