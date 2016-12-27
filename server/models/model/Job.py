from server.models.db import db, Model, mysql

class Job(Model):
    """ A background job."""
    statuses = ['queued', 'running', 'finished']

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
    log = db.Column(mysql.MEDIUMTEXT)  # All output, if the job has finished

