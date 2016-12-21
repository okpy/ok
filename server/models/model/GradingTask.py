from collections import namedtuple

from sqlalchemy.ext.hybrid import hybrid_property

from server.extensions import cache
from server.models.db import db, Model, transaction
from server.utils import chunks

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
        # Circular import
        from server.models import User

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
