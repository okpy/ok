import datetime
import json
from server.models import db, Assignment, Backup, Course, User, Version
from server.utils import encode_id
from server.forms import VersionForm

from tests import OkTestCase

class TestVersion(OkTestCase):

    def setUp(self):
        super().setUp()
        self.admin = User(email="admin@okpy.org", is_admin=True)
        db.session.add(self.admin)
        db.session.commit()

        old = Version(name="ok-client", current_version="v1.5.0",
            download_link="http://localhost/ok-client")
        db.session.add(old)
        db.session.commit()

    def test_version_form(self):
        self.login(self.admin.email)
        response = self.client.get('/admin/versions/ok-client')
        self.assert200(response)

        data = {
            "current_version": "v1.6.0",
            "download_link": "https://github.com/Cal-CS-61A-Staff/ok-client/releases/download/v1.5.4/ok"
        }

        response = self.client.post('/admin/versions/ok-client',
                        data=data, follow_redirects=True)

        assert response.status_code == 200

        new = Version.query.filter_by(name="ok-client").one()
        assert new.current_version == data['current_version']
        assert new.download_link == data['download_link']

        data = {
            "current_version": "v1.6.0",
            "download_link": "http://example.com/doesnotexist"
        }

        response = self.client.post('/admin/versions/ok-client',
                        data=data, follow_redirects=True)
        assert 'Invalid URL' in response.get_data(as_text=True)


    def test_version_permissions(self):
        self.setup_course()
        self.login(self.staff1.email)
        response = self.client.get('/admin/versions/ok-client')
        self.assertRedirects(response, '/admin/')

        data = {
            "current_version": "v1.6.0",
            "download_link": "https://github.com/Cal-CS-61A-Staff/ok-client/releases/download/v1.5.4/ok"
        }

        response = self.client.post('/admin/versions/ok-client', data=data)
        assert response.status_code != 200
        new = Version.query.filter_by(name="ok-client").one()
        assert new.current_version == "v1.5.0"

