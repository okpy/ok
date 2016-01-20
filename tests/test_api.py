import datetime
import json
from server.models import db, Assignment, Course, User

from .helpers import OkTestCase

class TestAuth(OkTestCase):
    def test_submit(self):
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
            }
        }

        response = self.client.post('/api/v3/backups/', data=json.dumps(data),
            headers=[('Content-Type', 'application/json')])
        backup = assignment.backups(user.id).first()
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
        assert not backup.submit

        data['submit'] = True
        response = self.client.post('/api/v3/backups/', data=json.dumps(data),
            headers=[('Content-Type', 'application/json')])
        submission = assignment.submissions(user.id).first()
        assert submission is not None

        self.assert_200(response)
        assert response.json['data'] == {
            'email': email,
            'key': submission.id,
            'course': course.id,
            'assignment': assignment.id
        }

        assert submission.assignment == assignment
        assert submission.submitter_id == user.id
        assert len(submission.messages) == len(data['messages'])
        assert submission.submit
