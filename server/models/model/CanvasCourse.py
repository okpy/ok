from server.models.db import db, Model

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
