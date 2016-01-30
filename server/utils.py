import server.models as models
from server.extensions import cache

# TODO : Better form of caching this.

def assignment_by_name(name, course_offering=None):
    """ Return assignment object when given a name. If a course offering is
    provided, the assignment name is prefixed by the course offering.
    """
    if course_offering:
        name = course_offering + '/' + name
    return models.Assignment.query.filter_by(name=name).one_or_none()

def course_by_name(name):
    return models.Course.query.filter_by(offering=name).one_or_none()
