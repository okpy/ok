from tests import OkTestCase

class TestQueue(OkTestCase):
    def test_dashboard_access(self):
        self.setup_course()
        response = self.client.get('/rq/')
        self.assertRedirects(response, '/login/')

        self.login(self.staff1.email)
        response = self.client.get('/rq/')
        self.assert_403(response)

        self.login(self.admin.email)
        response = self.client.get('/rq/')
        self.assert_200(response)
