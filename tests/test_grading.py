import datetime
from werkzeug.exceptions import BadRequest

from server.models import db, Backup, Group, Message, GradingTask
import server.utils as utils

from tests import OkTestCase

class TestGrading(OkTestCase):
    """Tests Grading/Queue Geneation."""
    def setUp(self):
        super(TestGrading, self).setUp()
        self.setup_course()

        message_dict = {'file_contents': {'backup.py': '1'}, 'analytics': {}}

        self.active_user_ids = [self.user1.id, self.user2.id, self.user3.id]
        self.active_staff = [self.staff1, self.staff2]

        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        # Creates 5 submissions per user, each spaced two minutes apart
        time = self.assignment.due_date - datetime.timedelta(minutes=30)
        num = 0
        for _ in range(5):
            for user_id in self.active_user_ids:
                num += 1
                time += datetime.timedelta(minutes=2)
                backup = Backup(submitter_id=user_id,
                    assignment=self.assignment, submit=True)
                messages = [Message(kind=k, backup=backup,
                    contents=m) for k, m in message_dict.items()]
                backup.created = time
                db.session.add_all(messages)
                db.session.add(backup)
                # Debugging print if tests fails
                print("User {} | Submission {} | Time {}".format(user_id, num, time))
        db.session.commit()

    def test_course_submissions(self):
        students, submissions, no_submission = self.assignment.course_submissions()
        self.assertEquals(sorted(list(students)), [2, 3, 4])
        self.assertEquals(sorted(list(no_submission)), [5, 6])
        self.assertEquals(sorted(list(submissions)), [14, 15])
        owners_by_backup = [(i, Backup.query.get(i).owners()) for i in submissions]
        self.assertEquals(sorted(owners_by_backup),  [(14, {2, 3}), (15, {4})])

    def test_flag(self):
        submission = self.assignment.submissions(self.active_user_ids).all()[10]
        self.assignment.flag(submission.id, self.active_user_ids)
        print("Flagged submission {}".format(submission.id))

        students, submissions, no_submission = self.assignment.course_submissions()
        self.assertEquals(sorted(list(students)), [2, 3, 4])
        self.assertEquals(sorted(list(no_submission)), [5, 6])
        self.assertEquals(sorted(list(submissions)), [submission.id, 15])
        owners_by_backup = [(i, Backup.query.get(i).owners()) for i in submissions]
        self.assertEquals(sorted(owners_by_backup),  [(submission.id, {2, 3}), (15, {4})])

    def test_queue_generation(self):
        students, backups, no_submissions = self.assignment.course_submissions()

        tasks = GradingTask.create_staff_tasks(backups, self.active_staff,
                                               self.assignment.id,
                                               self.assignment.course.id,
                                               "Composition")
        self.assertEquals(len(tasks), 2)
        self.assertEquals([t.grader.id for t in tasks], [self.staff1.id, self.staff2.id])

        # When only_unassigned is true, it should not add any new backups
        tasks = GradingTask.create_staff_tasks(backups, self.active_staff,
                                               self.assignment.id,
                                               self.assignment.course.id,
                                               "Composition", True)
        self.assertEquals(len(tasks), 0)
