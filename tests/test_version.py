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
    
    def test_version_form(self):
        old = Version(name="ok-client", current_version="v1.5.0",
            download_link="http://localhost/ok")
        db.session.add(old)
        db.session.commit()
        
        self.login(self.admin.email)
        
        data = {
            "current_version": "v1.6.0",
            "download_link": "https://github.com/Cal-CS-61A-Staff/ok-client/releases/download/v1.5.4/ok"
        }
        update_form = VersionForm(obj=old)
        update_form.current_version = data['current_version']
        update_form.download_link = data['download_link']
        
        response = self.client.post('/admin/client/ok-client',
                        data=data, follow_redirects=True,
                        headers=[('Content-Type', 'application/x-www-form-urlencoded')])
        
        assert response.status_code == 200
        
        new = Version.query.filter_by(name="ok-client").one()
        assert new.current_version == data['current_version']
        assert new.download_link == data['download_link']