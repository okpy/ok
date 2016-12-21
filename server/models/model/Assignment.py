from datetime import datetime as dt
from collections import namedtuple, Counter

from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import aliased
from sqlalchemy.sql import text
from werkzeug.exceptions import BadRequest

from server.constants import STAFF_ROLES, STUDENT_ROLE
from server.utils import generate_number_table
from server.extensions import cache
from server.models.db import db, Model, JsonBlob, StringList, transaction

from server.models import Backup
from server.models import Group
from server.models import GroupMember
from server.models import Message
from server.models import Score

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
