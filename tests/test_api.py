import datetime as dt
import json
from server.models import (db, Assignment, Backup, Course, User,
                           Version, Group)
from server.utils import encode_id

from tests import OkTestCase

class TestAuth(OkTestCase):
    def _test_backup(self, submit, delay=10, success=True):
        self.setup_course()

        email = self.user1.email
        self.login(email)
        user = User.lookup(email)

        course = self.course
        assignment = self.assignment
        # Offset the due date & lock_dates
        assignment.due_date = assignment.due_date + dt.timedelta(hours=delay)
        assignment.lock_date = assignment.lock_date + dt.timedelta(days=delay)

        okversion = Version(name="ok-client", current_version="v1.5.0",
            download_link="http://localhost/ok")
        db.session.add(okversion)
        db.session.commit()

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

        if success or not submit:
            assert response.json['data'] == {
                'email': email,
                'key': encode_id(backup.id),
                'course': {
                    'id': course.id,
                    'offering': course.offering,
                    'display_name': course.display_name,
                    'active': course.active,
                    'timezone': 'America/Los_Angeles'
                },
                'assignment': assignment.name
            }
            self.assert_200(response)

        if not success:
            self.assert_403(response)
            submit = False
            assert response.json['data'] == {
                'data': {
                    'backup': True,
                    'late': True
                }
            }


        assert backup.assignment == assignment
        assert backup.submitter_id == user.id
        assert len(backup.messages) == len(data['messages'])
        assert backup.submit == submit

    def test_backup(self):
        self._test_backup(False)

    def test_backup_after_deadline(self):
        self._test_backup(False, delay=-1)

    def test_submit(self):
        self._test_backup(True)

    def test_submit_after_deadline(self):
        self._test_backup(True, delay=-1, success=False)

    def test_api(self):
        response = self.client.get('/api/v3/')
        self.assert_200(response)
        assert response.json['data'] == {
            'version': 'v3',
            'url': '/api/v3/',
            'documentation': 'https://okpy.github.io/documentation',
            'github': 'https://github.com/Cal-CS-61A-Staff/ok'
        }
        assert response.json['message'] == 'success'
        assert response.json['code'] == 200

    def test_non_existant_api(self):
        response = self.client.get('/api/v3/doesnotexist')
        self.assert_404(response)
        assert response.json['data'] == {}
        assert response.json['code'] == 404

    def test_bad_hashid(self):
        self.setup_course()

        response = self.client.get('/api/v3/backups/xyzxyz/')
        self.assert_401(response)
        assert response.json['data'] == {}
        assert response.json['code'] == 401

        self.login(self.user1.email)
        response = self.client.get('/api/v3/backups/xyzxyz/')
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

    def test_score_anon(self):
        response = self.client.post('/api/v3/score/')
        self.assert_401(response)
        assert response.json['code'] == 401

    def test_score_student(self):
        self._test_backup(True)

        email = self.user1.email
        self.login(email)
        user = User.lookup(email)

        response = self.client.post('/api/v3/score/')
        self.assert_400(response)
        assert response.json['code'] == 400
        backup = Backup.query.filter(Backup.submitter_id == user.id).first()

        data = {'bid': encode_id(backup.id), 'kind': 'Total',
                'score': 128.2, 'message': 'wow'}
        response = self.client.post('/api/v3/score/', data=data)
        self.assert_401(response)
        assert response.json['code'] == 401

    def test_export_user(self):
        self._test_backup(True)
        student = User.lookup(self.user1.email)
        self.login(self.staff1.email)

        backup = Backup.query.filter(Backup.submitter_id == student.id).first()

        endpoint = '/api/v3/assignment/{0}/export/{1}'.format(self.assignment.name,
                                                          student.email)
        response = self.client.get(endpoint)
        self.assert_200(response)
        backups = response.json['data']['backups']
        self.assertEquals(len(backups), 1)
        self.assertEquals(response.json['data']['count'], 1)
        self.assertEquals(response.json['data']['limit'], 150)
        self.assertEquals(response.json['data']['offset'], 0)
        self.assertEquals(response.json['data']['has_more'], False)

        response = self.client.get(endpoint + "?offset=20&limit=2")
        self.assert_200(response)
        backups = response.json['data']['backups']
        self.assertEquals(len(backups), 0)
        self.assertEquals(response.json['data']['count'], 1)
        self.assertEquals(response.json['data']['limit'], 2)
        self.assertEquals(response.json['data']['offset'], 20)
        self.assertEquals(response.json['data']['has_more'], False)

    def test_export_final(self):
        self._test_backup(True)
        student = User.lookup(self.user1.email)

        backup = Backup.query.filter(Backup.submitter_id == student.id).first()
        endpoint = '/api/v3/assignment/{0}/submissions/'.format(self.assignment.name)

        response = self.client.get(endpoint)
        self.assert_403(response)

        self.login(self.staff1.email)
        response = self.client.get(endpoint)
        self.assert_200(response)
        backups = response.json['data']['backups']
        self.assertEquals(len(backups), 1)
        self.assertEquals(response.json['data']['count'], 1)
        self.assertEquals(response.json['data']['has_more'], False)
        self.assertEquals(response.json['data']['offset'], 0)

        response = self.client.get(endpoint + '?offset=1')
        self.assert_200(response)
        backups = response.json['data']['backups']
        self.assertEquals(len(backups), 0)
        self.assertEquals(response.json['data']['count'], 1)
        self.assertEquals(response.json['data']['has_more'], False)
        self.assertEquals(response.json['data']['offset'], 1)

    def test_assignment_api(self):
        self._test_backup(True)
        student = User.lookup(self.user1.email)
        endpoint = '/api/v3/assignment/{0}'.format(self.assignment.name)
        # View a public assignment
        response = self.client.get(endpoint)
        self.assert_200(response)
        # Change assignment to be hidden
        self.assignment.visible = False
        db.session.commit()
        response = self.client.get(endpoint)
        self.assert_403(response)

        self.assignment.visible = True
        db.session.commit()

        self.login(self.staff1.email)
        response = self.client.get(endpoint)
        self.assert_200(response)
        self.assertEquals(response.json['data']['name'], self.assignment.name)

        # Hidden assignment, but should be visible to staff
        self.assignment.visible = False
        db.session.commit()
        response = self.client.get(endpoint)
        self.assert_200(response)

        self.login(self.user1.email)
        self.assignment.visible = False
        db.session.commit()
        response = self.client.get(endpoint)
        self.assert_403(response)


    def test_group_api(self):
        self._test_backup(True)
        self.logout()

        student = User.lookup(self.user1.email)

        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)
        base_api = '/api/v3/assignment/{0}/group/{1}'
        endpoint = base_api.format(self.assignment.name, self.user1.email)

        response = self.client.get(endpoint)
        self.assert_401(response)

        self.login(self.user1.email)
        response = self.client.get(endpoint)
        self.assert_200(response)
        members = response.json['data']['members']
        self.assertEquals(len(members), 2)
        assert 'email' in members[0]['user']

        self.login(self.staff1.email)
        response = self.client.get(endpoint)

        self.assert_200(response)
        members = response.json['data']['members']
        self.assertEquals(len(members), 2)
        assert 'email' in  members[0]['user']

        # Login as some random user
        self.login(self.user3.email)
        response = self.client.get(endpoint)
        self.assert_403(response)

        # Check for existence of email
        response = self.client.get(base_api.format(self.assignment.name, 'oski61@example.com'))
        self.assert_403(response)

        self.login(self.admin.email)
        response = self.client.get(base_api.format(self.assignment.name, 'oski61@example.com'))
        self.assert_404(response)

    def test_score_staff(self):
        self._test_backup(True)

        user = User.lookup(self.user1.email)
        self.login(self.staff1.email)

        response = self.client.post('/api/v3/score/')
        self.assert_400(response)
        assert response.json['code'] == 400
        backup = Backup.query.filter(Backup.submitter_id == user.id).first()

        data = {'bid': encode_id(backup.id), 'kind': 'Total',
                'score': 128.2, 'message': 'wow'}
        response = self.client.post('/api/v3/score/', data=data)
        self.assert_200(response)
        assert response.json['code'] == 200

        self.logout()
        self.login(self.admin.email)

        data = {'bid': encode_id(backup.id), 'kind': 'Total',
                'score': 128.2, 'message': 'wow'}
        response = self.client.post('/api/v3/score/', data=data)
        self.assert_200(response)
        assert response.json['code'] == 200

    def test_user_api(self):
        self._test_backup(True)
        self.logout()

        student = User.lookup(self.user1.email)

        def test_both_endpoints(user):
            base_api = '/api/v3/user/{0}'
            user1_endpoint = base_api.format(user.email)
            current_user_endpoint = base_api.format('')

            current = self.client.get(current_user_endpoint)
            specific = self.client.get(user1_endpoint)

            return current, specific

        current, specific = test_both_endpoints(student)
        self.assert_401(current)
        self.assert_401(specific)

        # Should be able to view self
        self.login(self.user1.email)
        current, specific = test_both_endpoints(student)
        self.assert_200(current)
        self.assert_200(specific)

        members = current.json['data']['participations']
        self.assertEquals(len(members), 1)
        self.assertEquals(current.json['data'], specific.json['data'])

        # Staff don't get permission
        self.login(self.staff1.email)
        current, specific = test_both_endpoints(student)
        self.assert_200(current)
        self.assert_403(specific)

        # Login as some random user
        self.login(self.user3.email)
        current, specific = test_both_endpoints(student)
        self.assert_200(current)
        self.assert_403(specific)

        # Admins should have acess
        self.login(self.admin.email)
        current, specific = test_both_endpoints(student)
        self.assert_200(current)
        self.assert_200(specific)
        self.assertEquals(specific.json['data']['email'], student.email)

        # Lab Assistants don't have access
        self.login(self.lab_assistant1.email)
        current, specific = test_both_endpoints(student)
        self.assert_200(current)
        self.assert_403(specific)
