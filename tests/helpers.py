from flask.ext.testing import TestCase

from server import create_app
from server.models import db

class OkTestCase(TestCase):
    def create_app(self):
        return create_app('server.settings.test.TestConfig')

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self, email):
        """ Log in as an email address """
        response = self.client.post('/testing-login/authorized', data={
            'email': email
        }, follow_redirects=True)
        self.assert_200(response)
