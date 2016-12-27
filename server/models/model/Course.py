import pytz

from server.constants import STAFF_ROLES, TIMEZONE
from server.models.db import db, Model, Timezone
from server.models import Enrollment

class Course(Model):
    id = db.Column(db.Integer, primary_key=True)
    # offering - E.g., 'cal/cs61a/fa14'
    offering = db.Column(db.String(255), nullable=False, unique=True, index=True)
    institution = db.Column(db.String(255), nullable=False)  # E.g., 'UC Berkeley'
    display_name = db.Column(db.String(255), nullable=False)
    website = db.Column(db.String(255))
    active = db.Column(db.Boolean(), nullable=False, default=True)
    timezone = db.Column(Timezone, nullable=False, default=pytz.timezone(TIMEZONE))

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        if not obj:
            return False
        if action == "view":
            return user.is_authenticated
        return user.is_enrolled(obj.id, STAFF_ROLES)

    def __repr__(self):
        return '<Course {0!r}>'.format(self.offering)

    @staticmethod
    def by_name(name):
        return Course.query.filter_by(offering=name).one_or_none()

    @property
    def display_name_with_semester(self):
        year = self.offering[-2:]
        if "fa" in self.offering[-4:]:
            semester = "Fall"
        elif "sp" in self.offering[-4:]:
            semester = "Spring"
        else:
            semester = "Summer"
        return self.display_name + " ({0} 20{1})".format(semester, year)

    def is_enrolled(self, user):
        return Enrollment.query.filter_by(
            user=user,
            course=self
        ).count() > 0

    def get_staff(self):
        return [e for e in (Enrollment.query
                            .options(db.joinedload('user'))
                            .filter(Enrollment.role.in_(STAFF_ROLES),
                                    Enrollment.course == self)
                            .all()
                            )]
