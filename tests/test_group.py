import datetime

from server.models import db, Assignment, Course, Group, User

from .helpers import OkTestCase

# TODO: test for past lock date
class TestGroup(OkTestCase):
    def setUp(self):
        super(TestGroup, self).setUp()

        self.course = Course(offering='cal/cs61a/sp16')
        db.session.add(self.course)

        self.assignment = Assignment(
            name='cal/cs61a/sp16/proj1',
            course_id=self.course.id,
            display_name='Hog',
            due_date=datetime.datetime.now(),
            lock_date=datetime.datetime.now() + datetime.timedelta(days=1),
        )
        db.session.add(self.assignment)

        def make_student(n):
            user = User(email='student{0}@aol.com'.format(n))
            self.course.enroll(user)
            return user

        self.user1 = make_student(1)
        self.user2 = make_student(2)
        self.user3 = make_student(3)
        self.user4 = make_student(4)
        self.user5 = make_student(5)

    def test_invite(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        group = Group.lookup(self.user1)

        assert group.in_group(self.user1)
        assert group.has_status(self.user2, 'pending')
        assert group.size() == 2

        Group.invite(self.user1, self.user3, self.course, self.assignment)

        assert group.in_group(self.user1)
        assert group.has_status(self.user2, 'pending')
        assert group.has_status(self.user3, 'pending')
        assert group.size() == 3

    def test_invite_not_enrolled(self):
        not_enrolled = User(email='not_enrolled@aol.com')
        db.session.add(not_enrolled)

        self.assert_throws(Group.invite(self.user1, not_enrolled, self.course, self.assignment))
        self.assert_throws(Group.invite(not_enrolled, self.user1, self.course, self.assignment))

    def test_invite_wrong_assignment(self):
        wrong_assignment = Assignment()
        db.session.add(wrong_assignment)

        self.assert_throws(Group.invite(self.user1, self.user2, self.course, self.assignment))

    def test_invite_in_group(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)

        self.assert_throws(Group.invite(self.user1, self.user1, self.course, self.assignment))
        self.assert_throws(Group.invite(self.user1, self.user2, self.course, self.assignment))

        self.assert_throws(Group.invite(self.user2, self.user1, self.course, self.assignment))
        self.assert_throws(Group.invite(self.user2, self.user2, self.course, self.assignment))
        self.assert_throws(Group.invite(self.user2, self.user3, self.course, self.assignment))

        self.assert_throws(Group.invite(self.user3, self.user1, self.course, self.assignment))
        self.assert_throws(Group.invite(self.user3, self.user2, self.course, self.assignment))
        self.assert_throws(Group.invite(self.user3, self.user3, self.course, self.assignment))

    def test_invite_full(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        Group.invite(self.user1, self.user3, self.course, self.assignment)
        Group.invite(self.user1, self.user4, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.accept(self.user2)

        assert group.size() == 4
        self.assert_throws(Group.invite(self.user1, self.user5, self.course, self.assignment))

    def test_invite_individual(self):
        individual_assignment = Assignment(course=self.course.id)
        db.session.add(individual_assignment)

        self.assert_throws(Group.invite(self.user1, self.user2, self.course, self.assignment))

    def test_accept(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.accept(self.user2)

        assert group.has_status(self.user1, 'active')
        assert group.has_status(self.user2, 'active')
        assert group.size() == 2

    def test_accept_not_pending(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.accept(self.user2)

        self.assert_throws(BadRequest, group.accept(self.user2))
        self.assert_throws(BadRequest, group.accept(self.user3))

    def test_decline(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        Group.invite(self.user1, self.user3, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.accept(self.user2)
        group.decline(self.user3)

        assert group.has_status(self.user1, 'active')
        assert group.has_status(self.user2, 'active')
        assert not group.in_group(self.user3)
        assert group.size() == 2

    def test_decline_degenerate(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.decline(self.user2)

        assert Group.lookup(self.user1) is None
        assert Group.lookup(self.user2) is None

    def test_decline_not_pending(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.accept(self.user2)

        self.assert_throws(BadRequest, group.decline(self.user2))
        self.assert_throws(BadRequest, group.decline(self.user3))

    def test_remove(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        Group.invite(self.user1, self.user3, self.course, self.assignment)
        Group.invite(self.user1, self.user4, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.accept(self.user2)

        group.remove(self.user1, self.user2)
        assert group.has_status(self.user1, 'active')
        assert not group.in_group(self.user2)
        assert group.has_status(self.user3, 'pending')
        assert group.size() == 3

        group.remove(self.user1, self.user3)
        assert group.has_status(self.user1, 'active')
        assert not group.in_group(self.user3)
        assert group.size() == 2

    def test_remove_self(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        Group.invite(self.user1, self.user3, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.accept(self.user2)
        group.accept(self.user3)
        group.remove(self.user1, self.user1)

        assert not group.in_group(self.user1)
        assert group.has_status(self.user2, 'active')
        assert group.has_status(self.user3, 'active')

    def test_remove_degenerate(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        Group.invite(self.user1, self.user3, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.remove(self.user1, self.user1)

        assert not group.in_group(self.user1)
        assert not group.in_group(self.user2)
        assert not group.in_group(self.user3)

    def test_remove_not_in_group(self):
        Group.invite(self.user1, self.user2, self.course, self.assignment)
        group = Group.lookup(self.user1)
        group.accept(self.user2)

        self.assert_throws(BadRequest, group.remove(self.user2, self.user3))
        self.assert_throws(BadRequest, group.remove(self.user3, self.user2))
