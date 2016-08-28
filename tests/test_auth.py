import flask
import urllib.request

from tests import OkTestCase

class TestAuth(OkTestCase):
    email = 'martymcfly@aol.com'
    staff_email = 'okstaff@okpy.org'

    def test_ssl(self):
        response = urllib.request.urlopen('https://accounts.google.com')
        assert response.code == 200

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

    def test_sudo(self):
        """ Unauthorized users should not be able to sudo"""

        def attempt_sudo(email, expected, success):
            with self.client as c:
                response = c.get('/sudo/{0}/'.format(email))
                self.assertEqual(response.status_code, expected)
                s_user = flask.session.get('sudo-user')
                if success:
                    assert s_user
                else:
                    assert not s_user


        def attempt_suite(email, authorized=False):
            """ Try accessing a variety of users undo sudo mode. """

            if authorized:
                err_failure = 404
                err_success = 302
            elif not email:
                err_failure = 302
                err_success = 302
            else:
                err_success = 403
                err_failure = 403

            # Normal sudo logins
            if email: self.login(email)
            attempt_sudo(self.user1.email, err_success, authorized)
            self.logout()

            # Do not reveal existence of user unless admin
            if email: self.login(email)
            attempt_sudo("non@exist.com", err_failure, False)
            self.logout()

            # Check attempt to login as staff
            if email: self.login(email)
            attempt_sudo(self.staff1.email, err_success, authorized)
            self.logout()


        self.setup_course()

        # Login as student
        attempt_suite(self.user1.email, authorized=False)

        # Login as staff
        attempt_suite(self.staff_email, authorized=False)
        attempt_suite(self.staff1.email, authorized=False)

        # Login as admin
        attempt_suite(self.admin.email, authorized=True)

        # Login as lab assistant
        self.lab_assistant1 = make_lab_assistant(1)
        db.session.commit()
        attempt_suite(self.lab_assistant1.email, authorized=False)

        # Logged out user
        attempt_suite(None, authorized=False)
