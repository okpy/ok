from flask import Blueprint, render_template, flash, request, redirect, \
    url_for, session,  current_app, abort
from flask.ext.login import login_user, logout_user, login_required, \
    current_user

import functools

from server.constants import VALID_ROLES, STAFF_ROLES, STUDENT_ROLE
from server.extensions import cache
from server.models import User, Course, Assignment, Group, Backup, db
from server.utils import assignment_by_name, course_by_name

student = Blueprint('student', __name__)

def get_course(func):
    """ A decorator for routes to ensure that user is enrolled in the course.
    A user is enrolled if they are participating in the course
    with any role. Gets the course offering from the route's COURSE argument.
    Then binds the actual course object to the course keyword argument.

    Usage:
    @get_course # Get the course  from the cid param of the routes
    def my_route(course): return course.id
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        course = course_by_name(kwargs['course'])
        if not course:
            print("Course not found", kwargs['course'])
            return abort(404)
        kwargs['course'] = course
        enrolled = current_user.is_enrolled(course.id)
        if not enrolled and not current_user.is_admin:
            flash("You have not been added to this course on OK", "warning")
        return func(*args, **kwargs)
    return wrapper


@student.route("/")
@login_required
def index(auto_redir=True):
    enrollments = current_user.enrollments(VALID_ROLES)
    student_enrollments = [e for e in enrollments if e.role == STUDENT_ROLE]
    all_courses = Course.query.all()
    courses = {
        'instructor': [e.course for e in enrollments if e.role in STAFF_ROLES],
        'current': [e.course for e in student_enrollments if e.course.active],
        'past': [e.course for e in student_enrollments if not e.course.active],
        'all': all_courses,
        'num_enrolled': len(enrollments)
    }
    # Make the choice for users in one course
    if len(enrollments) == 1 and auto_redir:
        return redirect(url_for(".course", cid=enrollments[0].course_id))
    return render_template('student/courses/index.html', **courses)


@student.route("/<path:course>/")
@login_required
@get_course
def course(course):
    def assignment_info(assignment):
        # TODO does this make O(n) db queries?
        # TODO need group info too
        user_ids = assignment.active_user_ids(current_user.id)
        final_submission = assignment.final_submission(user_ids)
        submission_time = final_submission and final_submission.client_time
        return assignment, submission_time

    assignments = {
        'active': [assignment_info(a) for a in course.assignments if a.active],
        'inactive': [assignment_info(a) for a in course.assignments if not a.active]
    }
    return render_template('student/course/index.html', course=course,
                           **assignments)


@student.route("/<path:course>/assignments/")
@login_required
def assignments(course):
    return redirect(url_for(".course", course=course))

# CLEANUP : Really long route, used variable to keep lines under 80 chars.
ASSIGNMENT_DETAIL = "/<path:course>/assignments/<string:assign>/"

@student.route(ASSIGNMENT_DETAIL)
@login_required
@get_course
def assignment(course, assign):
    assign = assignment_by_name(assign, course.offering)
    if not assign:
        return abort(404)
    user_ids = assign.active_user_ids(current_user.id)
    backups = assign.backups(user_ids).limit(5).all()
    subms = assign.submissions(user_ids).limit(5).all()
    final_submission = assign.final_submission(user_ids)
    flagged = final_submission and final_submission.flagged
    return render_template('student/assignment/index.html', course=course,
            assignment=assign, backups=backups, subms=subms, flagged=flagged)

# TODO : Consolidate subm/backup list into one route? So many decorators ...
@student.route(ASSIGNMENT_DETAIL + "backups/", defaults={'submit': False})
@student.route(ASSIGNMENT_DETAIL + "submissions/", defaults={'submit': True})
@login_required
@get_course
def list_backups(course, assign, submit):
    assign = assignment_by_name(assign, course.offering)
    if not assign:
        abort(404)
    page = request.args.get('page', 1, type=int)
    user_ids = assign.active_user_ids(current_user.id)

    final_submission = assign.final_submission(user_ids)
    flagged = final_submission and final_submission.flagged

    if submit :
        # Submissions should take a flag for backups
        subms = assign.submissions(user_ids).paginate(page=page, per_page=10)
        return render_template('student/assignment/list.html', course=course,
                assignment=assign, subms=subms, flagged=flagged)

    backups = assign.backups(user_ids).paginate(page=page, per_page=10)
    return render_template('student/assignment/list.html', course=course,
            assignment=assign, backups=backups, flagged=flagged)

@student.route(ASSIGNMENT_DETAIL + "backups/<hashid:bid>/", defaults={'submit': False})
@student.route(ASSIGNMENT_DETAIL + "submissions/<hashid:bid>/", defaults={'submit': True})
@login_required
@get_course
def code(course, assign, bid, submit):
    assign = assignment_by_name(assign, course.offering)
    if not assign:
        abort(404)
    user_ids = assign.active_user_ids(current_user.id)
    backup = Backup.query.get(bid)
    if backup.submit != submit:
        abort(404)
    if backup and backup.can_view(current_user, user_ids, course):
        submitter = User.query.get(backup.submitter_id)
        file_contents = [m for m in backup.messages if
                            m.kind == "file_contents"]
        files = {}
        if file_contents:
            files = file_contents[0].contents
        else:
            flash("That code submission doesn't contain any code")
        backup_type = "Submission" if backup.submit else "Backup"
        return render_template('student/assignment/code.html', course=course,
                assignment=assign, backup=backup, submitter=submitter,
                files=files, backup_type=backup_type)
    else:
        flash("File doesn't exist (or you don't have permission)", "danger")
        abort(404)

@student.route(ASSIGNMENT_DETAIL + "submissions/<hashid:bid>/flag/", methods=['POST'])
@login_required
@get_course
def flag(course, assign, bid):
    assign = assignment_by_name(assign, course.offering)
    if assign:
        course = assign.course
        user_ids = assign.active_user_ids(current_user.id)
        flag = 'flag' in request.form
        next_url = request.form['next']
        if flag:
            assign.flag(bid, user_ids)
        else:
            assign.unflag(bid, user_ids)
        return redirect(next_url)
    else:
        abort(404)
