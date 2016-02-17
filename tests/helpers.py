import datetime
from flask.ext.testing import TestCase

from server import create_app
from server.models import db, Assignment, Course, Enrollment, User

class OkTestCase(TestCase):
    def create_app(self):
        return create_app('server.settings.test.TestConfig')

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self, email):
        """Log in as an email address."""
        response = self.client.post('/testing-login/authorized/', data={
            'email': email
        }, follow_redirects=True)
        self.assert_200(response)

    def setup_course(self):
        """Creates:

        * A course (self.course)
        * An assignment (self.assignment) in that course
        * 5 users (self.user1, self.user2, etc.) enrolled as students
        """
        self.course = Course(offering='cal/cs61a/sp16')
        self.assignment = Assignment(
            name='cal/cs61a/sp16/proj1',
            course=self.course,
            display_name='Hog',
            due_date=datetime.datetime.now(),
            lock_date=datetime.datetime.now() + datetime.timedelta(days=1),
            max_group_size=4)
        db.session.add(self.assignment)

        self.staff = User(email='okstaff@okpy.org', is_admin=True)
        participant = Enrollment(
            user=self.staff,
            course=self.course,
            role='staff')
        db.session.add(participant)


        def make_student(n):
            user = User(email='student{0}@aol.com'.format(n))
            participant = Enrollment(
                user=user,
                course=self.course)
            db.session.add(participant)
            return user

        self.user1 = make_student(1)
        self.user2 = make_student(2)
        self.user3 = make_student(3)
        self.user4 = make_student(4)
        self.user5 = make_student(5)
        db.session.commit()
