import csv

from sqlalchemy import PrimaryKeyConstraint

from server.constants import VALID_ROLES, STUDENT_ROLE, STAFF_ROLES
from server.extensions import cache
from server.models.db import db, Model, transaction

from server.models import User

class Enrollment(Model):
    __tablename__ = 'enrollment'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'course_id'),
    )

    user_id = db.Column(db.ForeignKey("user.id"), index=True, nullable=False)
    course_id = db.Column(db.ForeignKey("course.id"), index=True,
                          nullable=False)
    role = db.Column(db.Enum(*VALID_ROLES, name='role'),
                     default=STUDENT_ROLE, nullable=False, index=True)
    sid = db.Column(db.String(255))
    class_account = db.Column(db.String(255))
    section = db.Column(db.String(255))

    user = db.relationship("User", backref="participations")
    course = db.relationship("Course", backref="participations")

    export_items = ('sid', 'class_account', 'section')

    def has_role(self, course, role):
        if self.course != course:
            return False
        return self.role == role

    def is_staff(self, course):
        return self.course == course and self.role in STAFF_ROLES

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        return user.is_enrolled(obj.course.id, STAFF_ROLES)

    @staticmethod
    @transaction
    def enroll_from_form(cid, form):
        usr = User.lookup(form.email.data)
        if usr:
            form.populate_obj(usr)
        else:
            usr = User()
            form.populate_obj(usr)
            db.session.add(usr)
        db.session.commit()
        role = form.role.data
        info = {
            'id': usr.id,
            'sid': form.sid.data,
            'class_account': form.secondary.data,
            'section': form.section.data
        }
        Enrollment.create(cid, [info], role)

    @transaction
    def unenroll(self):
        cache.delete_memoized(User.is_enrolled)
        db.session.delete(self)

    @staticmethod
    @transaction
    def enroll_from_csv(cid, form):
        enrollment_info = []
        rows = form.csv.data.splitlines()
        role = form.role.data
        entries = list(csv.reader(rows))
        new_users = []
        existing_user_count = 0
        for usr in entries:
            email, name, sid, login, section = usr
            usr_obj = User.lookup(email)
            user_info = {
                "sid": sid,
                "class_account": login,
                "section": section
            }
            if not usr_obj:
                usr_obj = User(email=email, name=name)
                new_users.append(usr_obj)
            else:
                usr_obj.name = name
                existing_user_count += 1
            user_info['id'] = usr_obj
            enrollment_info.append(user_info)

        db.session.add_all(new_users)
        db.session.commit()
        for info in enrollment_info:
            info['id'] = info['id'].id
        Enrollment.create(cid, enrollment_info, role)
        return len(new_users), existing_user_count

    @staticmethod
    @transaction
    def create(cid, enrollment_info=None, role=STUDENT_ROLE):
        if enrollment_info is None:
            enrollment_info = []
        new_records = []
        for info in enrollment_info:
            usr_id, sid = info['id'], info['sid']
            class_account, section = info['class_account'], info['section']
            record = Enrollment.query.filter_by(user_id=usr_id,
                                                course_id=cid).one_or_none()
            if not record:
                record = Enrollment(course_id=cid, user_id=usr_id)
                new_records.append(record)

            record.role = role
            record.sid = sid
            record.class_account = class_account
            record.section = section

        db.session.add_all(new_records)

        cache.delete_memoized(User.is_enrolled)
