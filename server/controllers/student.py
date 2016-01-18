from flask import Blueprint, render_template, flash, request, redirect, \
    url_for, session,  current_app
from flask.ext.login import login_user, logout_user, login_required, \
    current_user

from server.constants import VALID_ROLES, STAFF_ROLES, STUDENT_ROLE
from server.extensions import cache
from server.models import User, db

student = Blueprint('student', __name__)


@student.route("/")
@login_required
def index():
    enrollments = current_user.enrollments(VALID_ROLES)
    student_enrollments = [e for e in enrollments if e.role == STUDENT_ROLE]
    courses = {
        'instructor': [e.course for e in enrollments if e.role in STAFF_ROLES],
        'current': [e.course for e in student_enrollments if e.course.active],
        'past': [e.course for e in student_enrollments if not e.course.active],
        'num_enrolled': len(enrollments)
    }
    # Make the choice for users in one course
    if len(enrollments) == 1:
        if courses['instructor']:
            return redirect(url_for("admin.course", cid=enrollments[0].id))
        else:
            return redirect(url_for(".course", cid=enrollments[0].id))
    return render_template('student/courses/index.html', **courses)


@student.route("/course/<int:cid>")
@login_required
def course(cid):
    return render_template('student/courses/index.html')
