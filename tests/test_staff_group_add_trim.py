from server.models import Group
from tests import OkTestCase

class TestStaffGroupAddTrim(OkTestCase):
    def setUp(self):
        super().setUp()
        self.setup_course()  # generates course, assignment, user1/user2/staff1

    def test_add_member_with_whitespace_email(self):
        self.login(self.staff1.email)

        url = f"/admin/course/{self.course.id}/{self.user1.email}/{self.assignment.id}/add_member"
        resp = self.client.post(url, data={"email": f"  {self.user2.email}  "}, follow_redirects=False)
        assert resp.status_code in (302, 303)

        group = Group.lookup(self.user1, self.assignment)
        assert group is not None
        assert group.has_status(self.user1, 'active')
        assert group.has_status(self.user2, 'active')