#pylint: disable=all

import os
os.environ['FLASK_CONF'] = 'TEST'
from test_base import BaseTestCase 
from test_base import make_fake_course
from test_base import make_fake_assignment
from test_base import make_fake_creator 

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import testbed

from app.utils import add_taskqueue, add_all_taskqueue, lease_tasks
from app.constants import STUDENT_ROLE
from app.constants import STAFF_ROLE
from app import models
from google.appengine.api import taskqueue

import json

#Mocks: Course
class AutograderTests(BaseTestCase):

    def get_students(self): 
        return {
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

    def get_messages(self): 
        return {
            'message0': models.Message(
                contents = json.dumps({"hello":0}),
                kind = 'file_contents'
                ),
            'message1': models.Message(
                contents = json.dumps({"hello1":1}),
                kind = 'file_contents'
                ),
            'message2': models.Message(
                contents = json.dumps({"hello2":2}),
                kind = 'file_contents'
                ),

        }

    def get_backups(self):
        return {
            "backup0": models.Backup(
                submitter = self.students["student0"].key,
                assignment= self.assignment.key,
                messages = [self.Messages['message0']]
            ),
            "backup1": models.Backup(
                submitter = self.students["student1"].key,
                assignment= self.assignment.key,
                messages = [self.Messages['message1']]
            ),
            "backup2": models.Backup(
                submitter = self.students["student2"].key,
                assignment= self.assignment.key,
                messages = [self.Messages['message2']]
            )
        }

    def get_submissions(self):
        return {
            "submission0": models.Submission(
                backup=self.Backups['backup0'].key
            ),
            "submission1": models.Submission(
                backup=self.Backups['backup1'].key
            ),
            "submission2": models.Submission(
                backup=self.Backups['backup2'].key
            )
        }

    def get_final_submissions(self):
        return {
            "submission0": models.FinalSubmission(
                assignment=self.assignment.key,
                submitter=self.students["student0"].key,
                submission=self.Submissions['submission0'].key
            ),
            "submission1": models.FinalSubmission(
                assignment=self.assignment.key,
                submitter=self.students["student1"].key,
                submission=self.Submissions['submission1'].key
            ),
            "submission2": models.FinalSubmission(
                assignment=self.assignment.key,
                submitter=self.students["student2"].key,
                submission=self.Submissions['submission2'].key
            )
        }
    def enroll(self, student, course, role):
        """Enroll student in course with the given role."""
        part = models.Participant()
        part.user = self.students[student].key
        part.course = course.key
        part.role = role
        part.put()

    def setUp(self):
        super(AutograderTests, self).setUp()
        self.creator = make_fake_creator()
        self.creator.put()
        self.course = make_fake_course(self.creator)
        self.course.put()
        self.assignment = make_fake_assignment(self.course, self.creator)
        self.assignment.put()

        self.students = self.get_students()

        for student in self.students.values():
            student.put()

        self.enroll("student0", self.course, STUDENT_ROLE)
        self.enroll("student1", self.course, STUDENT_ROLE)
        self.enroll("student2", self.course, STUDENT_ROLE)

        self.Messages = self.get_messages()

        for message in self.Messages.values():
            message.put()

        self.Backups = self.get_backups()

        for backup in self.Backups.values():
            backup.put()        

        self.Submissions = self.get_submissions()

        for sub in self.Submissions.values():
            sub.put()

        self.finalSubmissions = self.get_final_submissions()

        for submission in self.finalSubmissions.values():
            submission.put()

    def test_addToQueue_and_lease(self):
        add_all_taskqueue(self.course, self.assignment.key)
        q = taskqueue.Queue("pull-queue")
        files = lease_tasks()
        self.assertEquals(len(files), 3)             

        # for bac in backups:
        #     self.assertIn(bac, self.Backups.values())

    def test_add_taskqueue(self):
        add_taskqueue(self.Submissions['submission0'])
        q = taskqueue.Queue("pull-queue")
        files = lease_tasks()
        self.assertEquals(len(files), 1)             

if __name__ == "__main__":
    unittest.main()