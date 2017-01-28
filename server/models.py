# TODO: Split models into distinct .py files
from werkzeug.exceptions import BadRequest

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

from sqlalchemy import PrimaryKeyConstraint, MetaData, types
from sqlalchemy.dialects import mysql
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import aliased, backref
from sqlalchemy.sql import text

from markdown import markdown
import pytz

import functools

from collections import namedtuple, Counter

import contextlib
import csv
from datetime import datetime as dt
import json
import logging
import shlex
import urllib.parse
import mimetypes

from server.constants import (VALID_ROLES, STUDENT_ROLE, STAFF_ROLES, TIMEZONE,
                              SCORE_KINDS, OAUTH_OUT_OF_BAND_URI)

from server.extensions import cache, storage
from server.utils import (encode_id, chunks, generate_number_table,
                          humanize_name)

logger = logging.getLogger(__name__)

convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)


def transaction(f):
    """ Decorator for database (session) transactions."""
    @functools.wraps(f)
    def wrapper(*args, **kwds):
        try:
            value = f(*args, **kwds)
            db.session.commit()
            return value
        except:
            db.session.rollback()
            raise
    return wrapper


class Json(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return json.loads(value)


@compiles(mysql.MEDIUMBLOB, 'sqlite')
def ok_blob(element, compiler, **kw):
    return "BLOB"


@compiles(mysql.MEDIUMTEXT, 'sqlite')
def ok_text(element, compiler, **kw):
    return "TEXT"


class JsonBlob(types.TypeDecorator):
    impl = mysql.MEDIUMBLOB

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        return json.dumps(value).encode('utf-8')

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return json.loads(value.decode('utf-8'))


class Timezone(types.TypeDecorator):
    impl = types.String(255)

    def process_bind_param(self, value, dialect):
        # Python -> SQL
        if not hasattr(value, 'zone'):
            if value not in pytz.common_timezones_set:
                logger.warning('Unknown TZ: {}'.format(value))
                # Unknown TZ, use default instead
                return TIMEZONE
            return value
        return value.zone

    def process_result_value(self, value, dialect):
        # SQL -> Python
        return pytz.timezone(value)


class StringList(types.TypeDecorator):
    impl = types.Text

    def process_bind_param(self, string_list, dialect):
        # Python -> SQL
        items = []
        for item in string_list:
            if " " in item or not item:
                items.append('"{}"'.format(item))
            else:
                items.append(item)
        return ' '.join(items)

    def process_result_value(self, value, dialect):
        """ SQL -> Python
        Uses shlex.split to handle values with spaces.
        It's a fragile solution since it will break in some cases.
        For example if the last character is a backslash or otherwise meaningful
        to a shell.
        """
        values = []
        for val in shlex.split(value):
            if " " in val and '"' in val:
                values.append(val[1:-1])
            else:
                values.append(val)
        return values

class Model(db.Model):
    """ Timestamps all models, and serializes model objects."""
    __abstract__ = True

    created = db.Column(db.DateTime(timezone=True),
                        server_default=db.func.now(), nullable=False)

    def __repr__(self):
        if hasattr(self, 'id'):
            key_val = self.id
        else:
            pk = self.__mapper__.primary_key
            if type(pk) == tuple:
                key_val = pk[0].name
            else:
                key_val = self.__mapper__.primary_key._list[0].name
        return '<{0} {1}>'.format(self.__class__.__name__, key_val)

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        return False

    @hybrid_property
    def export(self):
        """ CSV export data. """
        if not hasattr(self, 'export_items'):
            return {}
        return {k: v for k, v in self.as_dict().items() if k in self.export_items}

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def from_dict(self, dict):
        for c in self.__table__.columns:
            if c.name in dict:
                setattr(self, c.name, dict[c.name])
        return self


class User(Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    is_admin = db.Column(db.Boolean(), default=False)

    export_items = ('email', 'name')

    def __repr__(self):
        return '<User {0}>'.format(self.email)

    def enrollments(self, roles=None):
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


class Assignment(Model):
    """ Assignments are particular to courses and have unique names.
        name - cal/cs61a/fa14/proj1
        display_name - Hog
        due_date - DEADLINE (Publically displayed)
        lock_date - DEADLINE+1 (Hard Deadline for submissions)
        url - cs61a.org/proj/hog/hog.zip
        flagged - User has indicated this one should be graded and not others
        published_scores - list of grade tags that are published to students
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index=True, nullable=False, unique=True)
    course_id = db.Column(db.ForeignKey("course.id"), index=True,
                          nullable=False)
    display_name = db.Column(db.String(255), nullable=False)
    due_date = db.Column(db.DateTime(timezone=True), nullable=False)
    lock_date = db.Column(db.DateTime(timezone=True), nullable=False)
    visible = db.Column(db.Boolean(), default=True)
    creator_id = db.Column(db.ForeignKey("user.id"))
    url = db.Column(db.Text)
    max_group_size = db.Column(db.Integer(), nullable=False, default=1)
    revisions_allowed = db.Column(db.Boolean(), nullable=False, default=False)
    autograding_key = db.Column(db.String(255))
    uploads_enabled = db.Column(db.Boolean(), nullable=False, default=False)
    upload_info = db.Column(db.Text)
    published_scores = db.Column(StringList, nullable=False, default=[])

    files = db.Column(JsonBlob)  # JSON object mapping filenames to contents
    course = db.relationship("Course", backref="assignments")

    user_assignment = namedtuple('UserAssignment',
                                 ['assignment', 'subm_time', 'group',
                                  'final_subm', 'scores'])

    @hybrid_property
    def active(self):
        return dt.utcnow() <= self.lock_date

    @classmethod
    def can(cls, obj, user, action):
        if not obj:
            if action == "create":
                return (user.enrollments(roles=STAFF_ROLES) or
                        user.is_admin)
            return False
        if user.is_admin:
            return True
        is_staff = user.is_enrolled(obj.course.id, STAFF_ROLES)
        if action == "view":
            return is_staff or obj.visible
        if action == "publish_scores":
            return is_staff
        return is_staff

    @staticmethod
    @cache.memoize(180)
    def assignment_stats(assign_id, detailed=True):
        assignment = Assignment.query.get(assign_id)
        base_query = Backup.query.filter_by(assignment=assignment)
        stats = {
            'submissions': base_query.filter_by(submit=True).count(),
            'backups': base_query.count(),
            'groups': Group.query.filter_by(assignment=assignment).count(),
        }
        data = assignment.course_submissions()
        submissions = [fs['backup'] for fs in data if fs['backup']]
        submissions_id = set(fs['id'] for fs in submissions)

        students_with_subms = set(s['user']['id'] for s in data
                                  if s['backup'] and s['backup']['submit'])
        students_with_backup = set(s['user']['id'] for s in data
                                   if s['backup'] and not s['backup']['submit'])
        students_without_subms = set(s['user']['id'] for s in data
                                     if not s['backup'])
        groups = [g['group'] for g in data if g['group']]
        total_students = len(data)
        percent_started = ((len(students_with_subms) + len(students_with_backup)) /
                           (total_students or 1)) * 100
        percent_finished = (len(students_with_subms) / (total_students or 1)) * 100
        active_groups = len({g['group_id'] for g in groups if ',' in g['group_member']})

        stats.update({
            'unique_submissions': len(submissions_id),
            'students_with_subm': len(students_with_subms),
            'students_with_backup': len(students_with_backup),
            'students_no_backup': len(students_without_subms),
            'percent_started': percent_started,
            'percent_finished': percent_finished,
            'active_groups': active_groups,
            'percent_groups_active': active_groups/(stats['groups'] or 1)
        })

        if detailed:
            stats.update({
                'raw_data': data
            })
        return stats

    @staticmethod
    @cache.memoize(1000)
    def name_to_assign_info(name):
        assign = Assignment.query.filter_by(name=name).one_or_none()
        if assign:
            info = assign.as_dict()
            info['active'] = assign.active
            return info

    @staticmethod
    def by_name(name):
        """ Return assignment object when given a name."""
        return Assignment.query.filter_by(name=name).one_or_none()

    def user_timeline(self, user_id):
        """ Timeline of user submissions. Returns a dictionary
        with timeline contents from most recent to oldest.
        Example Return:
        {'submitters': {'a@example.com': 40},
         'timeline': [{
            'event': "(Unlock|Started|Switched|Submitted|Later|Solved)"
            'attempt': 20,
            'title': "Started unlocking"
            'backup': Backup(...)
         }]
        }
        """
        user_ids = self.active_user_ids(user_id)
        analytics = (db.session.query(Backup, Message)
                       .outerjoin(Message)
                       .filter(Backup.submitter_id.in_(user_ids),
                               Backup.assignment_id == self.id,
                               Message.kind == "analytics")
                       .order_by(Backup.created.asc())
                       .all())

        unlock_started_q, started_questions, solved_questions = {}, {}, {}
        history, timeline, submitters = [], [], []
        # TODO: Make timeline a namedtuple
        last_q = (None, False, 0)  # current_question, is_solved, count

        for backup, message in analytics:
            contents = message.contents
            working_q = contents.get('question')
            if not working_q:
                continue
            curr_q = working_q[0]
            if ('history' not in contents or 'questions' not in contents['history'] or
                    not isinstance(contents['history']['questions'], dict)):
                continue

            submitters.append(backup.submitter.email)

            curr_q_stats = message.contents['history']['questions'].get(curr_q)
            total_attempt_count = message.contents['history'].get('all_attempts')
            is_solved = curr_q_stats.get('solved')
            if contents.get('unlock'):
                # Is unlocking.
                if curr_q not in unlock_started_q:
                    unlock_started_q[curr_q] = backup.hashid
                    timeline.append({"event": "Unlock",
                                     "attempt": total_attempt_count,
                                     "title": "Started unlocking {}".format(curr_q),
                                     "backup": backup})
                if curr_q != last_q[0]:
                    last_q = (curr_q, is_solved, 0)
                else:
                    last_q = (curr_q, is_solved, last_q[2]+1)
            elif curr_q not in started_questions:
                started_questions[curr_q] = backup.hashid
                timeline.append({"event": "Started",
                                 "title": "Started {}".format(curr_q),
                                 "attempt": total_attempt_count,
                                 "backup": backup})
                last_q = (curr_q, is_solved, 1)
            elif last_q[0] != curr_q and last_q[0] is not None:
                # Didn't just start it but did switch questions.
                timeline.append({"event": "Switched",
                                 "title": "Switched to {}".format(curr_q),
                                 "attempt": total_attempt_count,
                                 "body": "{} Backups Later".format(last_q[2]),
                                 "backup": backup, "date": backup.created})
                last_q = (curr_q, is_solved, 1)

            if is_solved and curr_q not in solved_questions:
                # Just solved a question
                solved_questions[curr_q] = backup.hashid
                attempts_later = last_q[2] - 1
                if attempts_later > 10:
                    timeline.append({"event": "Later",
                                     "title": ("{} attempts on {} after starting"
                                               .format(attempts_later, curr_q)),
                                     "attempt": total_attempt_count,
                                     "backup": backup})

                timeline.append({"event": "Solved",
                                 "title": "Solved {}".format(curr_q),
                                 "attempt": total_attempt_count,
                                 "backup": backup})
            else:
                last_q = (curr_q, is_solved, last_q[2]+1)

            if backup.submit:
                timeline.append({"event": "Submitted",
                                 "attempt": total_attempt_count,
                                 "title": "Submitted ({})".format(backup.hashid),
                                 "backup": backup})

            history.append(message.contents)

        return {'submitters': dict(Counter(submitters)),
                'timeline': timeline}

    def user_status(self, user, staff_view=False):
        """Return a summary of an assignment for a user. If STAFF_VIEW is True,
        return more information that staff can see also.
        """
        user_ids = self.active_user_ids(user.id)
        final_submission = self.final_submission(user_ids)
        submission_time = final_submission and final_submission.created
        group = Group.lookup(user, self)
        scores = self.scores(user_ids, only_published=not staff_view)
        return self.user_assignment(
            assignment=self,
            subm_time=submission_time,
            group=group,
            final_subm=final_submission,
            scores=scores,
        )

    def course_submissions(self, include_empty=True):
        """ Return data on all course submissions for all enrolled users
        List of dictionaries with user, group, backup dictionaries.
        Sample [ {'user': {}, 'group': {}, 'backup': {} }]
        """
        current_db = db.engine.name
        if current_db != 'mysql':
            return self.course_submissions_slow(include_empty=include_empty)

        # Can only run the fast query on MySQL
        submissions = []

        stats = self.mysql_course_submissions_query()
        keys = stats.keys()
        for r in stats:
            user_info = {k: v for k, v in zip(keys[:3], r[:3])}
            group_info = {k: v for k, v in zip(keys[3:6], r[3:6])}
            if group_info['group_member_emails']:
                group_info['group_member_emails'] = group_info['group_member_emails'].split(',')
            backup_info = {k: v for k, v in zip(keys[6:], r[6:])}
            if not include_empty and backup_info['id'] is None:
                continue
            data = {'user': user_info,
                    'group': group_info if group_info.get('group_id') else None,
                    'backup': backup_info if backup_info.get('id') else None}
            submissions.append(data)
        return submissions

    def mysql_course_submissions_query(self):
        """ For MySQL Clients only. Returns a SQLAlchemy result proxy object
        Contains all of the following fields.

        id  email   name                  group_id group_member group_member_emails
        5   dschmidt1@gmail.com 'david s' 3   5,15 dschmidt1@gmail.com, foo@bar.com

        created id  id submitter_id assignment_id submit  flagged
        2016-09-07 20:22:04 4790    15  1   1   1
        """
        giant_query = """SELECT * FROM
              (SELECT u.id,
                      u.email,
                      u.name,
                      gm.group_id,
                      GROUP_CONCAT(IFNULL(gm2.user_id, u.id)) AS group_member,
                      GROUP_CONCAT((SELECT partners.email from user as partners
                                    where id = gm2.user_id AND partners.id != u.id)) AS group_member_emails
               FROM
                 (SELECT u.id,
                         u.email,
                         u.name
                  FROM user AS u,
                               enrollment AS e
                  WHERE e.course_id = :course_id
                    AND e.user_id = u.id
                    AND e.role='student') AS u
               LEFT JOIN
                 (SELECT *
                  FROM group_member
                  WHERE status = 'active'
                    AND assignment_id = :assign_id) AS gm ON u.id = gm.user_id
               LEFT JOIN group_member AS gm2 ON gm2.group_id = gm.group_id
               AND gm2.status = 'active'
               GROUP BY u.id) AS members
            LEFT JOIN backup AS b2 ON b2.id=
              (SELECT id
               FROM backup AS b3,
                 ({group_number_table}) AS member_index_counter
               WHERE assignment_id=:assign_id
                 AND b3.submitter_id = CAST(NULLIF(SUBSTRING_INDEX(members.group_member, ',', -pos),
                                                   SUBSTRING_INDEX(members.group_member, ',', 1 - pos))
                                            AS UNSIGNED)
               ORDER BY flagged DESC, submit DESC, created DESC LIMIT 1)
               ORDER BY group_id DESC;
        """.format(group_number_table=generate_number_table(self.max_group_size))

        giant_query = text(giant_query)
        giant_query = giant_query.bindparams(db.bindparam("course_id", db.Integer),
                                             db.bindparam("assign_id", db.Integer))
        result = db.session.execute(giant_query, {'course_id': self.course.id,
                                                  'assign_id': self.id})
        return result

    def course_submissions_slow(self, include_empty=True):
        """ Return course submissions info with a slow set of queries."""
        seen = set()
        submissions = []
        for student in self.course.participations:
            if student.role == STUDENT_ROLE and student.user_id not in seen:
                student_user = student.user
                group_ids = self.active_user_ids(student.user_id)
                group_obj = Group.lookup(student_user, self)
                if group_obj:
                    group_members = [m.user for m in group_obj.members]
                else:
                    group_members = [student_user]
                group_emails = [u.email for u in group_members]
                group_member_ids = ','.join([str(u_id) for u_id in group_ids])

                fs = self.final_submission(group_ids)
                if not fs:
                    fs = self.backups(group_ids).first()

                for member in group_members:
                    if not fs and not include_empty:
                        continue
                    data = {
                        'user': {
                            'id': member.id,
                            'name': member.name,
                            'email': member.email,
                        },
                        'group': {
                            'group_id': group_obj.id,
                            'group_member': group_member_ids,
                            'group_member_emails': group_emails
                        } if group_obj else None,
                        'backup': fs.as_dict() if fs else None
                    }
                    submissions.append(data)
                seen |= group_ids  # Perform union of two sets
        return submissions

    def active_user_ids(self, user_id):
        """ Return a set of the ids of all users that are active in the same group
        that our user is active in. If the user is not in a group, return just
        that user's id (i.e. as if they were in a 1-person group).
        """
        user_member = aliased(GroupMember)
        members = GroupMember.query.join(
            user_member, GroupMember.group_id == user_member.group_id
        ).filter(
            user_member.user_id == user_id,
            user_member.assignment_id == self.id,
            user_member.status == 'active',
            GroupMember.status == 'active'
        ).all()
        if not members:
            return {user_id}
        else:
            return {member.user_id for member in members}

    def backups(self, user_ids):
        """ Return a query for the backups that the list of users has for this
        assignment.
        """
        return Backup.query.filter(
            Backup.submitter_id.in_(user_ids),
            Backup.assignment_id == self.id,
            Backup.submit == False
        ).order_by(Backup.created.desc())

    def submissions(self, user_ids):
        """ Return a query for the submissions that the list of users has for this
        assignment.
        """
        return Backup.query.filter(
            Backup.submitter_id.in_(user_ids),
            Backup.assignment_id == self.id,
            Backup.submit == True
        ).order_by(Backup.created.desc())

    def final_submission(self, user_ids):
        """ Return a final submission for a user, or None."""
        return (Backup.query
                      .options(db.joinedload(Backup.scores))
                      .filter(Backup.submitter_id.in_(user_ids),
                              Backup.assignment_id == self.id,
                              Backup.submit == True)
                      .order_by(Backup.flagged.desc(),
                                Backup.created.desc())
                      .first())

    def revision(self, user_ids):
        """ Return the revision backup for a user, or None."""
        revision_score = Score.query.filter(
            Score.user_id.in_(user_ids),
            Score.assignment_id == self.id,
            Score.kind == "revision",
            Score.archived == False,
        ).order_by(Score.created.desc()).first()

        if revision_score:
            return revision_score.backup

    def scores(self, user_ids, only_published=True):
        """Return a list of Scores for this assignment and a group. Only the
        maximum score for each kind is returned. If there is a tie, the more
        recent score is preferred.
        """
        scores = Score.query.filter(
            Score.user_id.in_(user_ids),
            Score.assignment_id == self.id,
            Score.archived == False,
        ).order_by(Score.score.desc(), Score.created.desc()).all()

        scores_by_kind = {}
        # keep only first score for each kind
        for score in scores:
            if score.kind not in scores_by_kind:
                scores_by_kind[score.kind] = score
        max_scores = list(scores_by_kind.values())
        if only_published:
            return [
                score for score in max_scores
                    if score.kind in self.published_scores
            ]
        else:
            return max_scores

    @transaction
    def flag(self, backup_id, member_ids):
        """ Flag a submission. First unflags any submissions by one of
        MEMBER_IDS, which is a list of group member user IDs.
        """
        self._unflag_all(member_ids)
        backup = Backup.query.filter(
            Backup.id == backup_id,
            Backup.submitter_id.in_(member_ids),
            Backup.flagged == False
        ).one_or_none()
        if not backup:
            raise BadRequest('Could not find backup')
        if not backup.submit:
            backup.submit = True
        backup.flagged = True
        return backup

    @transaction
    def unflag(self, backup_id, member_ids):
        """ Unflag a submission."""
        backup = Backup.query.filter(
            Backup.id == backup_id,
            Backup.submitter_id.in_(member_ids),
            Backup.flagged == True
        ).one_or_none()
        if not backup:
            raise BadRequest('Could not find backup')
        backup.flagged = False
        return backup

    def _unflag_all(self, member_ids):
        """ Unflag all submissions by members of MEMBER_IDS for
        this assignment (SELF)
        """
        # There should only ever be one flagged submission
        backup = Backup.query.filter(
            Backup.submitter_id.in_(member_ids),
            Backup.assignment_id == self.id,
            Backup.flagged == True
        ).one_or_none()
        if backup:
            backup.flagged = False

    @transaction
    def publish_score(self, tag):
        """Publish student score for the assignment."""
        self.published_scores = self.published_scores + [tag]

    @transaction
    def hide_score(self, tag):
        """Hide student score for the assignment."""
        self.published_scores = [t for t in self.published_scores if t != tag]



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
        role = form.role.data
        info = {
            'email': form.email.data,
            'name': form.name.data,
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
        for entry in csv.reader(rows):
            entry = [x.strip() for x in entry]
            enrollment_info.append({
                'email': entry[0],
                'name': entry[1],
                'sid': entry[2],
                'class_account': entry[3],
                'section': entry[4],
            })
        return Enrollment.create(cid, enrollment_info, role)

    @staticmethod
    @transaction
    def create(cid, enrollment_info, role=STUDENT_ROLE):
        """ENROLLMENT_INFO is a sequence of dictionaries with the keys
        'email', 'name', 'sid', 'class_account', and 'section'.
        Returns two integers, the number of enrollments created and the number
        of enrollments updated.
        """
        created = 0
        updated = 0
        for info in enrollment_info:
            email, name = info['email'], info['name']
            user = User.lookup(email)
            if user:
                user.name = name
            else:
                user = User(name=name, email=email)
                db.session.add(user)
            record = Enrollment.query.filter_by(user_id=user.id,
                                                course_id=cid).one_or_none()
            if not record:
                record = Enrollment(course_id=cid, user_id=user.id)
                created += 1
            else:
                updated += 1
            record.role = role
            record.sid = info['sid']
            record.class_account = info['class_account']
            record.section = info['section']
            db.session.add(record)
        cache.delete_memoized(User.is_enrolled)
        return created, updated

class Message(Model):
    __tablename__ = 'message'
    __table_args__ = {'mysql_row_format': 'COMPRESSED'}

    id = db.Column(db.Integer, primary_key=True)
    backup_id = db.Column(db.ForeignKey("backup.id"), nullable=False,
                          index=True)
    contents = db.Column(JsonBlob, nullable=False)
    kind = db.Column(db.String(255), nullable=False, index=True)

    backup = db.relationship("Backup")


class Backup(Model):
    id = db.Column(db.Integer, primary_key=True)

    submitter_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    # NULL if same as submitter
    creator_id = db.Column(db.ForeignKey("user.id"), nullable=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    submit = db.Column(db.Boolean(), nullable=False, default=False, index=True)
    flagged = db.Column(db.Boolean(), nullable=False, default=False, index=True)
    # The time we should treat this backup as being submitted. If NULL, use
    # the `created` timestamp instead.
    custom_submission_time = db.Column(db.DateTime(timezone=True), nullable=True)

    submitter = db.relationship("User", foreign_keys='Backup.submitter_id')
    creator = db.relationship("User", foreign_keys='Backup.creator_id')
    assignment = db.relationship("Assignment")
    messages = db.relationship("Message")
    scores = db.relationship("Score")
    comments = db.relationship("Comment", order_by="Comment.created")
    external_files = db.relationship("ExternalFile")

    # Already have indexes for submitter_id and assignment_id due to FK
    db.Index('idx_backupCreated', 'created')

    @classmethod
    def can(cls, obj, user, action):
        if action == "create":
            return user.is_authenticated
        elif not obj:
            return False
        elif user.is_admin:
            return True
        elif action == "view" and user.id in obj.owners():
            # Only allow group members to view
            return True
        return user.is_enrolled(obj.assignment.course.id, STAFF_ROLES)

    @hybrid_property
    def hashid(self):
        return encode_id(self.id)

    @hybrid_property
    def is_late(self):
        return self.submission_time > self.assignment.due_date

    @hybrid_property
    def active_scores(self):
        """Return non-archived scores."""
        return [s for s in self.scores if not s.archived]

    @hybrid_property
    def published_scores(self):
        """Return non-archived scores that are published to students."""
        return [s for s in self.scores
            if not s.archived and s.kind in self.assignment.published_scores]

    @hybrid_property
    def is_revision(self):
        return any(s for s in self.scores if s.kind == "revision")

    @hybrid_property
    def submission_time(self):
        if self.custom_submission_time:
            return self.custom_submission_time
        return self.created

    # @hybrid_property
    # def group(self):
    #     return Group.lookup(self.submitter, self.assignment)

    def owners(self):
        """ Return a set of user ids in the same group as the submitter."""
        return self.assignment.active_user_ids(self.submitter_id)

    def enrollment_info(self):
        """ Return enrollment info of users in this group.
        """
        owners = self.owners()
        course_id = self.assignment.course_id
        submitters = (Enrollment.query.options(db.joinedload(Enrollment.user))
                                .filter(Enrollment.user_id.in_(owners))
                                .filter(Enrollment.course_id == course_id)
                                .all())
        return submitters

    def files(self):
        """ Return a dictionary of filenames to contents."""
        message = Message.query.filter_by(
            backup_id=self.id,
            kind='file_contents').first()
        if message:
            contents = dict(message.contents)
            # submit is not a real file, but the client sends it anyway
            contents.pop('submit', None)
            return contents
        else:
            return {}

    def external_files_dict(self):
        """ Return a dictionary of filenames to ExternalFile objects """
        external = ExternalFile.query.filter_by(backup_id=self.id).all()
        return {f.filename: f for f in external}

    def analytics(self):
        """ Return a dictionary of filenames to contents."""
        message = Message.query.filter_by(
            backup_id=self.id,
            kind='analytics').first()
        if message:
            return dict(message.contents)
        else:
            return {}

    @staticmethod
    @cache.memoize(120)
    def statistics(self):
        return db.session.query(Backup).from_statement(
            db.text("""SELECT date_trunc('hour', backup.created), count(backup.id) FROM backup
            WHERE backup.created >= NOW() - '1 day'::INTERVAL
            GROUP BY date_trunc('hour', backup.created)
            ORDER BY date_trunc('hour', backup.created)""")).all()


class GroupMember(Model):
    """ A member of a group must accept the invite to join the group.
    Only members of a group can view each other's submissions.
    A user may only be invited or participate in a single group per assignment.
    The status value can be one of:
        pending - The user has been invited to the group.
        active  - The user accepted the invite and is part of the group.
    """
    __tablename__ = 'group_member'
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'assignment_id'),
    )
    status_values = ['pending', 'active']
    status_enum = db.Enum(*status_values, name="status")

    user_id = db.Column(db.ForeignKey("user.id"), nullable=False, index=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    group_id = db.Column(db.ForeignKey("group.id"), nullable=False, index=True)
    status = db.Column(status_enum, nullable=False, index=True)
    updated = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())

    user = db.relationship("User")
    assignment = db.relationship("Assignment")
    group = db.relationship("Group", backref=backref('members',
                                                     cascade="all, delete-orphan"))


class Group(Model):
    """ A group is a collection of users who are either members or invited.
    Groups are created when a member not in a group invites another member.
    Invited members may accept or decline invitations. Active members may
    revoke invitations and remove members (including themselves).
    A group must have at least 2 participants.
    Degenerate groups are deleted.
    """
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)

    assignment = db.relationship("Assignment")

    def size(self, status=None):
        return GroupMember.query.filter_by(group=self).count()

    def has_status(self, user, status):
        return GroupMember.query.filter_by(
            user=user,
            group=self,
            status=status
        ).count() > 0

    def is_pending(self):
        """ Returns a boolean indicating if group has an invitation pending.
        """
        return GroupMember.query.filter_by(
            group=self,
            status='pending'
        ).count() > 0

    def users(self):
        return [m.user for m in self.members]

    @staticmethod
    def lookup(user, assignment):
        member = GroupMember.query.filter_by(
            user=user,
            assignment=assignment
        ).one_or_none()
        if member:
            return member.group

    @staticmethod
    @transaction
    def force_add(staff, sender, recipient, assignment):
        """ Used by staff to create groups users on behalf of users."""
        group = Group.lookup(sender, assignment)
        add_sender = group is None
        if not group:
            group = Group(assignment=assignment)
            db.session.add(group)
        with group._log('accept', staff.id, recipient.id):
            if add_sender:
                group._add_member(sender, 'active')
            group._add_member(recipient, 'active')

    @staticmethod
    @transaction
    def force_remove(staff, sender, target, assignment):
        """ Used by staff to remove users."""
        group = Group.lookup(sender, assignment)
        if not group:
            raise BadRequest('No group to remove from')
        with group._log('remove', staff.id, target.id):
            group._remove_member(target)

    @staticmethod
    @transaction
    def invite(sender, recipient, assignment):
        """ Invite a user to a group, creating a group if necessary."""
        if not assignment.active:
            raise BadRequest('The assignment is past due')
        group = Group.lookup(sender, assignment)
        add_sender = group is None
        if not group:
            group = Group(assignment=assignment)
            db.session.add(group)
        elif not group.has_status(sender, 'active'):
            raise BadRequest('You are not in the group')
        with group._log('invite', sender.id, recipient.id):
            if add_sender:
                group._add_member(sender, 'active')
            group._add_member(recipient, 'pending')

    @transaction
    def remove(self, user, target_user):
        """ Remove a user from the group.
        The user must be an active member in the group, and the target user
        must be an active or pending member. You may remove yourself to leave
        the group. The assignment must also be active.
        """
        if not self.assignment.active:
            raise BadRequest('The assignment is past due')
        if not self.has_status(user, 'active'):
            raise BadRequest('You are not in the group')
        with self._log('remove', user.id, target_user.id):
            self._remove_member(target_user)

    @transaction
    def accept(self, user):
        """ Accept an invitation."""
        if not self.assignment.active:
            raise BadRequest('The assignment is past due')
        member = GroupMember.query.filter_by(
            user=user,
            group=self,
            status='pending'
        ).one_or_none()
        if not member:
            raise BadRequest('{0} is not invited to this group'.format(user.email))
        with self._log('accept', user.id, user.id):
            member.status = 'active'
        self.assignment._unflag_all([user.id])

    @transaction
    def decline(self, user):
        """ Decline an invitation."""
        if not self.assignment.active:
            raise BadRequest('The assignment is past due')
        with self._log('decline', user.id, user.id):
            self._remove_member(user)

    def _add_member(self, user, status):
        if self.size() >= self.assignment.max_group_size:
            raise BadRequest('This group is full')
        if not self.assignment.course.is_enrolled(user):
            raise BadRequest('{0} is not enrolled'.format(user.email))
        member = GroupMember.query.filter_by(
            user=user,
            assignment=self.assignment
        ).one_or_none()
        if member:
            raise BadRequest('{0} is already in a group'.format(user.email))
        member = GroupMember(
            user_id=user.id,
            group=self,
            assignment=self.assignment,
            status=status)
        db.session.add(member)

    def _remove_member(self, user):
        member = GroupMember.query.filter_by(
            user=user,
            group=self
        ).one_or_none()
        if not member:
            raise BadRequest('{0} is not in this group'.format(user.email))
        db.session.delete(member)
        if self.size() <= 1:
            db.session.delete(self)

    def serialize(self):
        """ Turn the group into a JSON object with:
        - id: the group id
        - assignment_id: the assignment id
        - members: a list of objects, with keys
            - user_id: the user id
            - status: the user's status ("pending" or "active")
        """
        members = GroupMember.query.filter_by(group_id=self.id).all()
        return {
            'id': self.id,
            'assignment_id': self.assignment_id,
            'members': [{
                'user_id': member.user_id,
                'status': member.status
            } for member in members]
        }

    @contextlib.contextmanager
    def _log(self, action_type, user_id, target_id):
        """ Usage:

        with self._log('invite', user_id, target_id):
            ...
        """
        before = self.serialize()
        yield
        after = self.serialize()
        action = GroupAction(
            action_type=action_type,
            user_id=user_id,
            target_id=target_id,
            group_before=before,
            group_after=after)
        db.session.add(action)


class GroupAction(Model):
    """ A group event, for auditing purposes. All group activity is logged."""
    action_types = ['invite', 'accept', 'decline', 'remove']

    id = db.Column(db.Integer, primary_key=True)
    action_type = db.Column(db.Enum(*action_types, name='action_type'), nullable=False)
    # user who initiated request
    user_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    # user whose status was affected
    target_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    # see Group.serialize for format
    group_before = db.Column(Json, nullable=False)
    group_after = db.Column(Json, nullable=False)

class Version(Model):
    id = db.Column(db.Integer(), primary_key=True)
    # software name e.g. 'ok'
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    current_version = db.Column(db.String(255))
    download_link = db.Column(db.Text())

    @staticmethod
    @cache.memoize(1800)
    def get_current_version(name):
        version = Version.query.filter_by(name=name).one_or_none()
        if version:
            return version.current_version, version.download_link
        return None, None


class Comment(Model):
    """ Composition comments. Line is the line # on the Diff.
    Submission_line is the closest line on the submitted file.
    """
    id = db.Column(db.Integer(), primary_key=True)
    updated = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())
    backup_id = db.Column(db.ForeignKey("backup.id"), index=True, nullable=False)
    author_id = db.Column(db.ForeignKey("user.id"), nullable=False)

    filename = db.Column(db.String(255), nullable=False)
    line = db.Column(db.Integer(), nullable=False)  # Line of the original file

    message = db.Column(mysql.MEDIUMTEXT)  # Markdown

    backup = db.relationship("Backup")
    author = db.relationship("User")

    @classmethod
    def can(cls, obj, user, action):
        if action == "create":
            return user.is_authenticated
        if user.is_admin:
            return True
        if not obj:
            return False
        if action == "view" and user.id in obj.backup.owners():
            # Only allow group members to view
            return True
        if action == "edit" and user.id == obj.author_id:
            # Only allow non-staff to delete their own comments
            return True
        return user.is_enrolled(obj.assignment.course.id, STAFF_ROLES)

    @property
    def formatted(self):
        return markdown(self.message)


class Score(Model):
    id = db.Column(db.Integer, primary_key=True)
    grader_id = db.Column(db.ForeignKey("user.id"), nullable=False)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), nullable=False)
    backup_id = db.Column(db.ForeignKey("backup.id"), nullable=False, index=True)
    # submitter of score's backup
    user_id = db.Column(db.ForeignKey("user.id"), nullable=False)

    kind = db.Column(db.String(255), nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    message = db.Column(mysql.MEDIUMTEXT)
    public = db.Column(db.Boolean, default=True)
    archived = db.Column(db.Boolean, default=False, index=True)

    backup = db.relationship("Backup")
    grader = db.relationship("User", foreign_keys='Score.grader_id')
    user = db.relationship("User", foreign_keys='Score.user_id')
    assignment = db.relationship("Assignment")

    export_items = ('assignment_id', 'kind', 'score', 'message',
                    'backup_id', 'grader')

    @hybrid_property
    def export(self):
        """ CSV export data. Overrides Model.export."""
        data = self.as_dict()
        data['backup_id'] = encode_id(self.backup_id)
        data['grader'] = User.email_by_id(self.grader_id)
        return {k: v for k, v in data.items() if k in self.export_items}

    @hybrid_property
    def students(self):
        """ The users to which this score applies."""
        return [User.query.get(owner) for owner in self.backup.owners()]

    @classmethod
    def can(cls, obj, user, action):
        if user.is_admin:
            return True
        course = obj.assignment.course
        if action == "get":
            return obj.backup.can_view(user, course)
        return user.is_enrolled(course.id, STAFF_ROLES)

    def archive(self, commit=True):
        self.public = False
        self.archived = True

        if commit:
            db.session.commit()

    @transaction
    def archive_duplicates(self):
        """ Archive scores with of the same kind on the same backup.
        TODO: Investigate doing automatically on create/save.
        """
        existing_scores = Score.query.filter_by(backup=self.backup,
                                                kind=self.kind,
                                                archived=False).all()
        for old_score in existing_scores:
            if old_score.id != self.id:  # Do not archive current score
                old_score.archive(commit=False)


class GradingTask(Model):
    """ Each task represent a single submission assigned to a grader."""
    id = db.Column(db.Integer(), primary_key=True)
    assignment_id = db.Column(db.ForeignKey("assignment.id"), index=True,
                              nullable=False)
    kind = db.Column(db.String(255), default="composition")
    backup_id = db.Column(db.ForeignKey("backup.id"), nullable=False)
    course_id = db.Column(db.ForeignKey("course.id"))
    grader_id = db.Column(db.ForeignKey("user.id"), index=True)
    score_id = db.Column(db.ForeignKey("score.id"))

    backup = db.relationship("Backup", backref="grading_tasks")
    assignment = db.relationship("Assignment")
    grader = db.relationship("User")
    course = db.relationship("Course")
    score = db.relationship("Score")

    @hybrid_property
    def is_complete(self):
        return self.score_id is not None
        # return self.kind in [s.tag for s in self.backup.scores]

    @hybrid_property
    def total_tasks(self):
        tasks = (GradingTask.query
                            .filter_by(grader_id=self.grader_id,
                                       assignment_id=self.assignment_id)
                            .count())
        return tasks

    @hybrid_property
    def completed(self):
        completed = (GradingTask.query
                                .filter_by(grader_id=self.grader_id,
                                           assignment_id=self.assignment_id)
                                .filter(GradingTask.score_id)
                                .count())
        return completed

    @hybrid_property
    def remaining(self):
        ungraded = (GradingTask.query
                               .filter_by(grader_id=self.grader_id,
                                          assignment_id=self.assignment_id,
                                          score_id=None)
                               .count())
        return ungraded

    def get_next_task(self):
        ungraded = (GradingTask.query
                               .filter_by(grader_id=self.grader_id,
                                          assignment_id=self.assignment_id,
                                          score_id=None)
                               .order_by(GradingTask.created.asc())
                               .first())
        return ungraded

    @classmethod
    def get_staff_tasks(cls, assignment_id):
        """ Return list of namedtuple objects that represent queues.
            Only uses 1 SQL Query.
            Attributes:
                - grader: User, assigned grader
                - completed: int, completed tasks
                - remaining: int, ungraded tasks
        """
        tasks = (db.session.query(cls,
                                  db.func.count(cls.score_id),
                                  db.func.count())
                           .options(db.joinedload('grader'))
                           .group_by(cls.grader_id)
                           .filter_by(assignment_id=assignment_id)
                           .all())
        Queue = namedtuple('Queue', 'grader completed total')

        queues = [Queue(grader=q[0].grader, completed=q[1],
                        total=q[2]) for q in tasks]

        # Sort by number of outstanding tasks
        queues.sort(key=lambda q: q.total - q.completed, reverse=True)
        return queues

    @classmethod
    @transaction
    def create_staff_tasks(cls, backups, staff, assignment_id, course_id, kind):
        # Filter out backups that have a GradingTasks
        backups = [b for b in backups if not cls.query.filter_by(backup_id=b).count()]

        paritions = chunks(list(backups), len(staff))
        tasks = []
        for assigned_backups, grader in zip(paritions, staff):
            for backup_id in assigned_backups:
                task = cls(kind=kind, backup_id=backup_id, course_id=course_id,
                           assignment_id=assignment_id, grader=grader)
                tasks.append(task)
                cache.delete_memoized(User.num_grading_tasks, grader)
        db.session.add_all(tasks)
        return tasks


class Client(Model):
    """ OAuth Clients.
    See: https://flask-oauthlib.readthedocs.io/en/latest/oauth2.html
    """
    name = db.Column(db.String(40))

    # human readable description, not required
    description = db.Column(db.String(400))

    # creator of the client, not required
    user_id = db.Column(db.ForeignKey('user.id'))
    # required if you need to support client credential
    user = db.relationship('User')

    client_id = db.Column(db.String(40), primary_key=True)
    client_secret = db.Column(db.String(55), unique=True, index=True,
                              nullable=False)

    is_confidential = db.Column(db.Boolean, nullable=False)

    redirect_uris = db.Column(StringList, nullable=False)
    default_scopes = db.Column(StringList, nullable=False)

    @property
    def default_redirect_uri(self):
        return self.redirect_uris[0]

    def validate_redirect_uri(self, redirect_uri):
        if redirect_uri == OAUTH_OUT_OF_BAND_URI:
            return True
        # always allow loopback hosts
        parse_result = urllib.parse.urlparse(redirect_uri)
        if parse_result.hostname in ('localhost', '127.0.0.1'):
            return True
        return redirect_uri in self.redirect_uris

class Grant(Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = db.relationship('User')

    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')

    code = db.Column(db.String(255), index=True, nullable=False)

    redirect_uri = db.Column(db.String(255))
    expires = db.Column(db.DateTime)

    scopes = db.Column(StringList)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self


class Token(Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(
        db.String(40), db.ForeignKey('client.client_id'),
        nullable=False,
    )
    client = db.relationship('Client')

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id')
    )
    user = db.relationship('User')

    # currently only bearer is supported
    token_type = db.Column(db.String(40))

    access_token = db.Column(db.String(255), unique=True)
    refresh_token = db.Column(db.String(255), unique=True)
    expires = db.Column(db.DateTime)
    scopes = db.Column(StringList)

    def delete(self):
        db.session.delete(self)
        db.session.commit()
        return self


class Job(Model):
    """ A background job."""
    statuses = ['queued', 'running', 'finished']
    result_kinds = ['html', 'string', 'link']

    id = db.Column(db.Integer, primary_key=True)
    updated = db.Column(db.DateTime(timezone=True), onupdate=db.func.now())
    status = db.Column(db.Enum(*statuses, name='status'), nullable=False)

    # The user who started the job.
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )
    user = db.relationship('User')

    course_id = db.Column(
        db.Integer, db.ForeignKey('course.id'), nullable=False, index=True
    )
    course = db.relationship('Course')

    name = db.Column(db.String(255), nullable=False)  # The name of the function
    # Human-readable description of the job
    description = db.Column(db.Text, nullable=False)
    failed = db.Column(db.Boolean, nullable=False, default=False)
    log = db.Column(mysql.MEDIUMTEXT)  # Log output, if the job has finished

    result_kind = db.Column(db.Enum(*result_kinds, name='result_kind'), default='string')
    result = db.Column(mysql.MEDIUMTEXT)  # Final output, if the job did not crash

##########
# Canvas #
##########

class CanvasCourse(Model):
    id = db.Column(db.Integer, primary_key=True)
    # The API domain (e.g. bcourses.berkeley.edu or canvas.instructure.com)
    api_domain = db.Column(db.String(255), nullable=False)
    # The ID of the course for the Canvas API
    external_id = db.Column(db.Integer, nullable=False)
    # API access token
    access_token = db.Column(db.String(255), nullable=False)

    course_id = db.Column(
        db.Integer, db.ForeignKey('course.id'),
        index=True, nullable=False,
    )
    course = db.relationship('Course')

    # Don't export access token
    export_items = ('api_domain', 'external_id', 'course_id')

    @staticmethod
    def by_course_id(course_id):
        return CanvasCourse.query.filter_by(course_id=course_id).one_or_none()

    @property
    def url(self):
        return 'https://{}/courses/{}'.format(self.api_domain, self.external_id)

class CanvasAssignment(Model):
    id = db.Column(db.Integer, primary_key=True)
    # The ID of the assignment for the Canvas API
    external_id = db.Column(db.Integer, nullable=False)
    score_kinds = db.Column(StringList, nullable=False, default=[])

    canvas_course_id = db.Column(
        db.Integer, db.ForeignKey('canvas_course.id'),
        index=True, nullable=False,
    )
    canvas_course = db.relationship('CanvasCourse', backref='canvas_assignments')

    assignment_id = db.Column(
        db.Integer, db.ForeignKey('assignment.id'),
        index=True, nullable=False,
    )
    assignment = db.relationship('Assignment')

    @property
    def url(self):
        return '{}/assignments/{}'.format(self.canvas_course.url, self.external_id)

#########
# Files #
#########

class ExternalFile(Model):

    id = db.Column(db.Integer, primary_key=True)
    # Bucket/Folder that the file is stored in
    container = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(1024), nullable=False)
    object_name = db.Column(db.String(1024), nullable=False)

    staff_file = db.Column(db.Boolean, nullable=False, index=True)
    deleted = db.Column(db.Boolean, nullable=False, default=False)

    course_id = db.Column(
        db.Integer, db.ForeignKey('course.id'), index=True, nullable=False
    )
    course = db.relationship('Course')

    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), index=True, nullable=False
    )
    user = db.relationship('User')

    assignment_id = db.Column(
        db.Integer, db.ForeignKey('assignment.id'), index=True
    )
    assignment = db.relationship('Assignment')

    backup_id = db.Column(
        db.Integer, db.ForeignKey('backup.id'), index=True
    )
    backup = db.relationship('Backup')

    def object(self):
        return storage.get_blob(self.object_name, self.container)

    @property
    def mimetype(self):
        guess = mimetypes.guess_type(self.filename)
        if not guess[0]:
            return 'application/octet-stream'
        return guess[0]

    @property
    def download_link(self):
        return '/files/{}'.format(encode_id(self.id))

    def delete(self):
        self.object().delete()
        self.deleted = True
        db.session.commit()

    @staticmethod
    def upload(iterable, user_id, name, staff_file=True, course_id=None,
               assignment_id=None, backup=None, **kwargs):
        object = storage.upload(iterable, name=name, **kwargs)
        external_file = ExternalFile(
            container=storage.container_name,
            filename=name,
            object_name=object.name,
            course_id=course_id,
            assignment_id=assignment_id,
            user_id=user_id,
            backup=backup,
            staff_file=False)
        db.session.add(external_file)
        db.session.commit()
        return external_file

    @classmethod
    def can(cls, obj, user, action):
        if not user:
            return False
        if user.is_admin:
            return True

        # Files that don't exist
        if not obj and action == "create":
            return True
        elif not obj:
            return False
        is_staff_member = user.is_enrolled(obj.course_id, STAFF_ROLES)

        # Staff can see staff & student files
        if is_staff_member:
            return True
        elif obj.staff_file:
            return False

        # Student files are visible to the creators and group members
        if user.id == obj.user_id:
            return True
        elif obj.assignment_id:
            group_members = obj.assignment.active_user_ids(obj.user_id)
            return user.id in group_members
        return False
