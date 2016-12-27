from server.models.db import db, Model, StringList

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
