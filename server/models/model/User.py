from sqlalchemy.ext.hybrid import hybrid_property
from flask_login import UserMixin

from server.constants import VALID_ROLES, STUDENT_ROLE
from server.utils import humanize_name
from server.models.db import db, Model
from server.extensions import cache

from server.models import GradingTask

class User(Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    is_admin = db.Column(db.Boolean(), default=False)

    export_items = ('email', 'name')

    def __repr__(self):
        return '<User {0}>'.format(self.email)

    def enrollments(self, roles=None):
        from server.models import Enrollment  # Cicrular import hack!!!!!
        if roles is None:
            roles = [STUDENT_ROLE]
        query = (Enrollment.query.options(db.joinedload('course'))
                           .filter(Enrollment.user_id == self.id)
                           .filter(Enrollment.role.in_(roles)))
        return query.all()

    @cache.memoize(120)
    def is_enrolled(self, course_id, roles=VALID_ROLES):
        for enroll in self.participations:
            if enroll.course_id == course_id and enroll.role in roles:
                return enroll
        return False

    @hybrid_property
    def identifier(self):
        return humanize_name(self.name) or self.email

    @cache.memoize(3600)
    def num_grading_tasks(self):
        # TODO: Pass in assignment_id (Useful for course dashboard)
        return GradingTask.query.filter_by(grader=self, score_id=None).count()

    @staticmethod
    def get_by_id(uid):
        """ Performs .query.get; potentially can be cached."""
        return User.query.get(uid)

    @staticmethod
    @cache.memoize(240)
    def email_by_id(uid):
        user = User.query.get(uid)
        if user:
            return user.email

    @staticmethod
    def lookup(email):
        """ Get a User with the given email address, or None."""
        return User.query.filter_by(email=email).one_or_none()
