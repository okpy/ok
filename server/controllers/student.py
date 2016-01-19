from flask import Blueprint, render_template, flash, request, redirect, \
    url_for, session,  current_app
from flask.ext.login import login_user, logout_user, login_required, \
    current_user

import functools

from server.constants import VALID_ROLES, STAFF_ROLES, STUDENT_ROLE
from server.extensions import cache
from server.models import User, Course, Assignment, db


student = Blueprint('student', __name__)


@student.route("/")
@login_required
def index(auto_redir=True):
    enrollments = current_user.enrollments(VALID_ROLES)
    student_enrollments = [e for e in enrollments if e.role == STUDENT_ROLE]
    courses = {
        'instructor': [e.course for e in enrollments if e.role in STAFF_ROLES],
        'current': [e.course for e in student_enrollments if e.course.active],
        'past': [e.course for e in student_enrollments if not e.course.active],
        'num_enrolled': len(enrollments)
    }
    # Make the choice for users in one course
    if len(enrollments) == 1 and auto_redir:
        return redirect(url_for(".course", cid=enrollments[0].course_id))
    return render_template('student/courses/index.html', **courses)


def is_enrolled(func):
    """ A decorator for routes to ensure that user is enrolled in
    the course. Gets the course id from the named arg cid of the route.
    A user is enrolled if they are participating in the course with any role.

    Usage:
    @is_enrolled # Get the course id from the cid param of the routes
    def my_route(cid): ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        course_id = kwargs['cid']
        enrolled = current_user.is_enrolled(course_id)
        if not enrolled and not current_user.is_admin:
            flash("You have not been added to this course on OK", "warning")
        return func(*args, **kwargs)
    return wrapper


@student.route("/course/<int:cid>")
@login_required
@is_enrolled
def course(cid):
    course = Course.query.get(cid)
    assignments = {
        'active': [a for a in course.assignments if a.active],
        'inactive': [a for a in course.assignments if not a.active]
    }
    return render_template('student/course/index.html', course=course,
                           **assignments)

@student.route("/course/<int:cid>/assignment/<int:aid>")
@login_required
@is_enrolled
def assignment(cid, aid):
    assgn = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if assgn:
        course = assgn.course
        return render_template('student/course/index.html', course=course,
                               assignment=assgn)
    else:
        flash("That assignment does not exist", "warning")
        return

@student.route("/course/<int:cid>/assignment/<int:aid>/submission/<int:bid>")
@login_required
@is_enrolled
def submisison(cid, aid, bid):
    assgn = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if assgn:
        course = assgn.course

        return render_template('student/assignment/code.html', course=course,
                               assignment=assgn)
    else:
        flash("That assignment does not exist", "warning")
        return
