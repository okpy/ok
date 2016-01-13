from flask.ext.testing import TestCase

from server import create_app
from server.models import db

class OkTestCase(TestCase):
    def create_app(self):
        return create_app('server.settings.TestConfig')

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()