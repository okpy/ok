from tests import OkTestCase

from server.models import db, User

class TestUser(OkTestCase):
    def test_lookup(self):
        email = 'martymcfly@aol.com'

        user = User.lookup(email)
        assert user is None

        db.session.add(User(email=email))
        db.session.commit()

        user = User.lookup(email)
        assert user.email == email
