import datetime
import json
from server.models import db, Assignment, Backup, Course, User, Version
from server.utils import encode_id
from server.forms import VersionForm

from tests import OkTestCase

class TestAssignment(OkTestCase):

    def setUp(self):
        super().setUp()
        self.setup_course()

    def test_new_assignment(self):

        self.login(self.admin.email)

        data = {
            "display_name": "test",
            "name": "{}/test".format(self.course.offering),
            "due_date": "2016-09-14 23:59:59",
            "lock_date": "2016-09-15 23:59:59",
            "max_group_size": 1,
            "visible": True
        }

        response = self.client.post("admin/course/1/assignments/new",
                        data=data, follow_redirects=True)

        self.assert200(response)
        self.assert_template_used('staff/course/assignment/assignment.template.html')


    def test_new_assignment_not_visible(self):

        self.login(self.admin.email)

        data = {
            "display_name": "test",
            "name": "{}/test".format(self.course.offering),
            "due_date": "2016-09-14 23:59:59",
            "lock_date": "2016-09-15 23:59:59",
            "max_group_size": 1
        }

        response = self.client.post("admin/course/1/assignments/new",
                        data=data, follow_redirects=True)

        self.assert200(response)
        self.assertTemplateUsed('staff/course/assignment/assignments.html')

