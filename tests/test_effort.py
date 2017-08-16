from server.models import db, Backup, Extension, Group, Score
import server.utils as utils
from server import generate
from server import constants
from server.controllers import api
from server import jobs
from server.jobs.effort import grade_on_effort, effort_score, get_submission_time

from itertools import zip_longest
import datetime as dt

from tests import OkTestCase

class TestEffortGrading(OkTestCase):
    """Tests Grading/Queue Generation."""
    def setUp(self):
        super().setUp()
        self.setup_course()
        self.curr_time = dt.datetime.utcnow()

    def make_backup(self, grading=None, attempts=None, submit=False, time=None):
        """
        Create a Backup with specific message info.

        ``grading`` is a string where each character is a grade for a question:

            'c' - correct
            'p' - passed at least one testcase
            'f' - failed
            ' ' - omitted

        ``attempts`` is a string where each character is the number of attempts
        for a question:

            '#' - number of attempts
            ' ' - omitted

        ``submit`` where the Backup is a submission
        """
        grading = grading or ''
        attempts = attempts or ''
        custom_time = time or self.curr_time
        messages = {
            'grading': {
                q: {
                    'failed': 0 if result == 'c' else 1,
                    'locked': 0 if result == 'c' else 1,
                    'passed': 1 if result == 'p' else 0
                }
                for q, result in enumerate(grading) if result != ' '
            },
            'analytics': {
                'history': {
                    'questions': {
                q: {
                    'solved': result == 'c',
                    'attempts': int(n) if n != ' ' else 0
                }
                for q, (result, n) in enumerate(zip_longest(grading, attempts, fillvalue=' '))
                    if not (result == ' ' and n == ' ')
                    }
                }
            }
        }
        backup = api.make_backup(self.user1, self.assignment.id, messages, submit)
        backup.created = custom_time
        db.session.commit()
        return backup

    def score_equals(self, backup, score, qs=2):
        try:
            effort, _ = effort_score(backup, 2, qs)
        except AssertionError:
            effort = 0
        self.assertEquals(effort, score)

    def test_effort_grading(self):
        """
        Full credit if question is correct or at least one testcase passed
        """
        self.score_equals(self.make_backup(), 0)

        self.score_equals(self.make_backup(grading='cc'), 2)
        self.score_equals(self.make_backup(grading='cp'), 2)
        self.score_equals(self.make_backup(grading='pp'), 2)
        self.score_equals(self.make_backup(grading='pf'), 1)
        self.score_equals(self.make_backup(grading='p'), 1)
        self.score_equals(self.make_backup(grading=' p'), 1)

    def test_effort_attempts(self):
        """
        Full credit if question has at least three attempts
        """
        self.score_equals(self.make_backup(grading='ff', attempts='33'), 2)
        self.score_equals(self.make_backup(grading='ff', attempts='32'), 1)
        self.score_equals(self.make_backup(grading='fc', attempts='32'), 2)
        self.score_equals(self.make_backup(grading='cf', attempts='32'), 1)
        self.score_equals(self.make_backup(grading='pf', attempts='11'), 1)
        self.score_equals(self.make_backup(grading='ff', attempts='39'), 2)
        self.score_equals(self.make_backup(grading='ff', attempts='3'), 1)
        self.score_equals(self.make_backup(attempts='3'), 1)
        self.score_equals(self.make_backup(attempts='53'), 2)
        self.score_equals(self.make_backup(attempts='13'), 1)

    def test_effort_ceil(self):
        """
        Points should ceil to nearest point (no decimals)
        """
        self.score_equals(self.make_backup(grading='c'), 1, qs=3)    # 0.5 -> 1
        self.score_equals(self.make_backup(grading='ffc'), 1, qs=3)  # 0.5 -> 1
        self.score_equals(self.make_backup(grading='fcc'), 2, qs=3)  # 1.5 -> 2
        self.score_equals(self.make_backup(attempts='111'), 0, qs=3) # 0.0 -> 0

    def test_effort_missing(self):
        self.score_equals(self.make_backup(grading='f c', attempts='33'), 2, qs=3) # 2
        self.score_equals(self.make_backup(grading='p', attempts=' 3'), 2)


    def _make_ext(self, assignment, user, time=None):
        custom_time = time or self.curr_time
        ext = Extension.create(assignment=assignment, user=user,
                custom_submission_time=custom_time,
                expires=self.curr_time,
                staff=self.staff1)
        return ext

    def test_extension_submission_time(self):
        self.assignment.due_date = self.curr_time - dt.timedelta(days=1)
        backup = self.make_backup(time=self.curr_time - dt.timedelta(hours=1))

        # Submission time shouldn't initially be on time
        self.assertFalse(backup.submission_time <= self.assignment.due_date)

        ext = self._make_ext(self.assignment, self.user1, time=self.assignment.due_date)

        # Should use the extension's time instead of the backup's time
        self.assertTrue(backup.submission_time <= self.assignment.due_date)

    def test_scores_group(self):
        self.assignment.due_date = self.curr_time + dt.timedelta(days=1)

        Group.invite(self.user1, self.user2, self.assignment)
        group = Group.lookup(self.user1, self.assignment)
        group.accept(self.user2)

        backup = self.make_backup(grading='cc')
        job_id = jobs.enqueue_job(
            grade_on_effort,
            description='test effort job',
            course_id=self.course.id,
            user_id=self.admin.id,
            assignment_id=self.assignment.id,
            full_credit=3,
            late_multiplier=0,
            required_questions=2,
            grading_url='http://example.com/'
        ).id
        self.run_jobs()

        score1 = Score.query.filter_by(
                kind='effort',
                user=self.user1,
                assignment=self.assignment).first().score
        self.assertEquals(score1, 3)

        score2 = Score.query.filter_by(
                kind='effort',
                user=self.user2,
                assignment=self.assignment).first().score
        self.assertEquals(score2, 3)


