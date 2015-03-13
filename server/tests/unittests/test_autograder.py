import os
os.environ['FLASK_CONF'] = 'TEST'
from test_base import BaseTestCase, make_fake_course, make_fake_assignment, make_fake_creator #pylint: disable=relative-import
from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

from app.utils import add_taskqueue
from app.constants import STUDENT_ROLE, STAFF_ROLE
from app import models
from google.appengine.api import taskqueue

#Mocks: Course
class AutograderTests(BaseTestCase):

    def enroll(self, student, course, role):
        """Enroll student in course with the given role."""
        part = models.Participant()
        part.user = self.students[student].key
        part.course = course.key
        part.role = role
        part.put()

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.creator = make_fake_creator()
        self.creator.put()
        self.course = make_fake_course(self.creator)
        self.course.put()
        self.assignment = make_fake_assignment(self.course, self.creator)
        self.assignment.put()

        self.students = {
            "student0": models.User(
                email=["dummy@student.com"],
            ),
            "student1": models.User(
                email=["other@student.com"],
            ),
            "student2": models.User(
                email=["otherrr@student.com"],
            )
        }

        for student in self.students.values():
            student.put()

        self.enroll("student0", self.course, STUDENT_ROLE)
        self.enroll("student1", self.course, STUDENT_ROLE)
        self.enroll("student2", self.course, STUDENT_ROLE)

        self.finalSubmissions = {
            "submission0": models.FinalSubmission(
                assignment=self.assignment.key,
                submitter=self.students["student0"].key
            ),
            "submission1": models.FinalSubmission(
                assignment=self.assignment.key,
                submitter=self.students["student1"].key
            ),
            "submission2": models.FinalSubmission(
                assignment=self.assignment.key,
                submitter=self.students["student2"].key
            )
        }

        for submission in self.finalSubmissions.values():
            student.put()

    def test_addToQueue(self):
        add_taskqueue(self.course, self.assignment.key)
        q = taskqueue.Queue("pull-queue")
        tasks = q.lease_tasks(10, 10)
        for t in tasks:
            self.assertIn(t.paylaod, self.finalSubmissions.values())

if __name__ == "__main__":
    unittest.main()