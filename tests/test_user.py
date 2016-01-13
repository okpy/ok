from .helpers import OkTestCase

from server.models import User

class TestUser(OkTestCase):
    def test_from_email(self):
        email = 'martymcfly@aol.com'

        user1 = User.from_email(email)
        assert user1.email == email
        assert not user1.is_admin
        assert user1.active

        user2 = User.from_email(email)
        assert user1.id == user2.id
