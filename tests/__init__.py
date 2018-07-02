import datetime as dt
import functools
import os
import socket
import unittest
import redis

from flask_rq import get_worker
from flask_testing import TestCase

from server import create_app
from server.models import db, Assignment, Course, Enrollment, User
from server import constants

class OkTestCase(TestCase):
    def create_app(self):
        return create_app('test')

    def setUp(self):
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self, email):
        """Log in as an email address."""
        self.logout()
        response = self.client.post('/testing-login/authorized/', data={
            'email': email
        }, follow_redirects=True)
        self.assert_200(response)

    def logout(self):
        """Logout in testing mode."""
        response = self.client.post('/testing-login/logout/', follow_redirects=True)
        self.assert_200(response)
        self.assert_template_used('index.html')

    def make_student(self, n, section=None):
        user = User(email='student{0}@aol.com'.format(n))
        participant = Enrollment(user=user, course=self.course, section=section)
        db.session.add(participant)
        return user

    def make_staff(self, n, role=constants.STAFF_ROLE, section=None):
        user = User(email='staff{0}@bitdiddle.net'.format(n))
        participant = Enrollment(user=user, course=self.course, role=role, section=section)
        db.session.add(participant)
        return user

    def make_lab_assistant(self, n, role=constants.LAB_ASSISTANT_ROLE):
        user = User(email='lab_assistant{0}@labassist.net'.format(n))
        participant = Enrollment(user=user, course=self.course, role=role)
        db.session.add(participant)
        return user

    def setup_course(self):
        """Creates:

        * A course (self.course)
        * 2 assignments (self.assignment) in that course
        * 5 users (self.user1, self.user2, etc.) enrolled as students
        * 2 staff members (self.staff1, self.staff2) as TAs
        * 1 lab assistant (self.lab_assistant1) as lab assistants
        * 1 Admin (okadmin@okpy.org)
        """
        self.admin = User(email='okadmin@okpy.org', is_admin=True)
        db.session.add(self.admin)
        db.session.commit()

        self.course = Course(
            offering='cal/cs61a/sp16',
            institution='UC Berkeley',
            display_name='CS 61A')
        self.assignment = Assignment(
            name='cal/cs61a/sp16/proj1',
            creator_id=self.admin.id,
            course=self.course,
            display_name='Hog',
            due_date=dt.datetime.utcnow(),
            lock_date=dt.datetime.utcnow() + dt.timedelta(days=1),
            max_group_size=4,
            autograding_key='test')  # AG responds with a 200 if ID = 'test'
        db.session.add(self.assignment)

        self.assignment2 = Assignment(
            name='cal/cs61a/sp16/proj2',
            creator_id=self.admin.id,
            course=self.course,
            display_name='Maps',
            due_date=dt.datetime.utcnow() + dt.timedelta(days=2),
            lock_date=dt.datetime.utcnow() + dt.timedelta(days=3),
            max_group_size=3)
        db.session.add(self.assignment2)

        def make_student(n, section=None):
            user = User(email='student{0}@aol.com'.format(n))
            participant = Enrollment(user=user, course=self.course, section=section)
            db.session.add(participant)
            return user

        def make_staff(n, role=constants.STAFF_ROLE, section=None):
            user = User(email='staff{0}@bitdiddle.net'.format(n))
            participant = Enrollment(user=user, course=self.course, role=role, section=section)
            db.session.add(participant)
            return user

        def make_lab_assistant(n, role=constants.LAB_ASSISTANT_ROLE):
            user = User(email='lab_assistant{0}@labassist.net'.format(n))
            participant = Enrollment(user=user, course=self.course, role=role)
            db.session.add(participant)
            return user

        self.user1 = make_student(1)
        self.user2 = make_student(2)
        self.user3 = make_student(3)
        self.user4 = make_student(4)
        self.user5 = make_student(5)
        self.user6 = make_student(6, section=1)
        self.user7 = make_student(7, section=2)
        self.user8 = make_student(8, section=2)

        self.staff1 = make_staff(1)
        self.staff2 = make_staff(2)
        self.staff3 = make_staff(3, section=1)
        self.staff4 = make_staff(4, section=2)

        self.lab_assistant1 = make_lab_assistant(1)

        db.session.commit()

    def run_jobs(self):
        get_worker().work(burst=True)
        db.session.expire_all()


def skipIfWindows(test_func):
    is_windows = os.name == 'nt'
    reason = 'This test uses OS features not supported by Windows'
    return unittest.skipIf(is_windows, reason)(test_func)


def skipUnlessRedisIsAvailable(test_func):
    @functools.wraps(test_func)
    def redis_availability_check_decorator(self, *args, **kwargs):

        if "REDIS_URL" in self.app.config:
            client = redis.Redis.from_url(self.app.config["REDIS_URL"])
        elif "REDIS_HOST" in self.app.config:
            redis_host = self.app.config['REDIS_HOST']
            redis_port = self.app.config['REDIS_PORT']

            redis_socket = socket.socket()
            redis_socket.settimeout(1)
            try:
                redis_socket.connect((redis_host, redis_port))
            except (socket.error, socket.timeout):
                reason = 'Redis is not available. Did you start redis-server?'
                raise unittest.SkipTest(reason)
        else:
            reason = 'Redis is not configured!'
            raise unittest.SkipTest(reason)

        return test_func(self, *args, **kwargs)

    return redis_availability_check_decorator
