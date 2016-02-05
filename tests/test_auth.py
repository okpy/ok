from .helpers import OkTestCase

class TestAuth(OkTestCase):
    email = 'martymcfly@aol.com'

    def test_login(self):
        """GET /login/ should redirect to Google OAuth."""
        response = self.client.get('/login/')
        assert response.location.startswith('https://accounts.google.com/o/oauth2/auth')

    def test_testing_login(self):
        """GET /testing-login/ should show a test login page."""
        response = self.client.get('/testing-login/')
        self.assert_200(response)
        self.assert_template_used('testing-login.html')

    def test_testing_login_fail(self):
        """GET /testing-login/ should 404 if TESTING_LOGIN config is not set."""
        app = self.create_app()
        app.config['TESTING_LOGIN'] = False
        response = app.test_client().get('/testing-login/')
        self.assert_404(response)

    def test_restricted(self):
        """User should see courses on / if logged in, but not if logged out."""
        # Load Landing Page
        response = self.client.get('/')
        self.assert_200(response)
        self.assert_template_used('index.html')
        assert self.email not in str(response.data)

        self.login(self.email)
        response = self.client.get('/')
        self.assert_200(response)
        assert self.email in str(response.data)
        assert 'Courses | Ok' in str(response.data)
