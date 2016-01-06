from flask import Blueprint, render_template, flash, request, redirect, \
    url_for, session,  current_app, abort

from flask.ext.login import login_required, current_user
from functools import wraps

from server.models import User, Course, Participant, db
from server.constants import STAFF_ROLES

admin = Blueprint('admin', __name__)


def is_staff(func, courses=[]):
    """ Provide user object to API methods. Passes USER as a keyword argument
        to all protected API Methods.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            roles = current_user.enrollments(roles=STAFF_ROLES)
            if len(roles) > 0 or current_user.is_admin:
                return func(*args, **kwargs)
        flash("You are not on course staff", "error")
        return redirect(url_for("student.index"))
    return wrapper


@admin.route("/")
@is_staff
def index():
    enrollments = current_user.enrollments(roles=STAFF_ROLES)
    courses = [e.course for e in enrollments]
    return render_template('staff/index.html', courses=courses)
