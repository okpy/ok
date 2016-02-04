from flask import Blueprint, render_template, flash, request, redirect, \
    url_for, session,  current_app, abort
from flask.ext.login import login_user, logout_user, login_required, \
    current_user
from werkzeug.exceptions import BadRequest

import functools

from server.constants import VALID_ROLES, STAFF_ROLES, STUDENT_ROLE
from server.extensions import cache
from server.forms import CSRFForm
from server.models import User, Course, Assignment, Group, Backup, db
from server.utils import is_safe_redirect_url

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
        course = Course.by_name(kwargs['course'])
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
        return redirect(url_for(".course", course=enrollments[0].course.offering))
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
        group = Group.lookup(current_user, assignment)
        return assignment, submission_time, group

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
    assign = Assignment.by_name(assign, course.offering)
    if not assign:
        return abort(404)

    user_ids = assign.active_user_ids(current_user.id)
    fs = assign.final_submission(user_ids)
    group = Group.lookup(current_user, assign)
    can_invite = assign.max_group_size > 1
    can_remove = group and group.has_status(current_user, 'active')

    if group:
        can_invite = len(group.members) < assign.max_group_size

    data = {
        'course': course,
        'assignment': assign,
        'backups' : assign.backups(user_ids).limit(5).all(),
        'subms' : assign.submissions(user_ids).limit(5).all(),
        'final_submission' : fs,
        'flagged' : fs and fs.flagged,
        'group' : group,
        'can_invite': can_invite,
        'can_remove': can_remove,
        'csrf_form': CSRFForm()
    }
    return render_template('student/assignment/index.html', **data)

@student.route(ASSIGNMENT_DETAIL + "<bool(backups, submissions):submit>/")
@login_required
@get_course
def list_backups(course, assign, submit):
    assign = Assignment.by_name(assign, course.offering)
    if not assign:
        abort(404)
    page = request.args.get('page', 1, type=int)
    user_ids = assign.active_user_ids(current_user.id)
    csrf_form = CSRFForm()

    if submit:
        backups = assign.submissions(user_ids)
    else:
        backups = assign.backups(user_ids)
    paginate = backups.paginate(page=page, per_page=10)
    return render_template('student/assignment/list.html', course=course,
            assignment=assign, paginate=paginate, submit=submit, csrf_form=csrf_form)

@student.route(ASSIGNMENT_DETAIL + "<bool(backups, submissions):submit>/<hashid:bid>/")
@login_required
@get_course
def code(course, assign, submit, bid):
    assign = Assignment.by_name(assign, course.offering)
    if not assign:
        abort(404)
    user_ids = assign.active_user_ids(current_user.id)
    backup = Backup.query.get(bid)
    if not (backup and backup.submit == submit and backup.can_view(current_user, user_ids, course)):
        abort(404)
    use_diff = request.args.get('diff', False)
    return render_template('student/assignment/code.html',
        course=course, assignment=assign, backup=backup, use_diff=use_diff,
        files_before=assign.files(), files_after=backup.files())

@student.route(ASSIGNMENT_DETAIL + "submissions/<hashid:bid>/flag/", methods=['POST'])
@login_required
@get_course
def flag(course, assign, bid):
    assign = Assignment.by_name(assign, course.offering)
    if assign:
        course = assign.course
        user_ids = assign.active_user_ids(current_user.id)
        flag = 'flag' in request.form
        next_url = request.form['next']
        if flag:
            assign.flag(bid, user_ids)
        else:
            assign.unflag(bid, user_ids)
        if is_safe_redirect_url(request, next_url):
            return redirect(next_url)
        else:
            flash("Not a valid redirect", "danger")
            abort(400)
    else:
        abort(404)

@student.route(ASSIGNMENT_DETAIL + "group/invite/", methods=['POST'])
@login_required
@get_course
def group_invite(course, assign):
    assignment = Assignment.by_name(assign, course.offering)
    if not assignment:
        abort(404)
    email = request.form['email']
    invitee = User.lookup(email)
    if not invitee:
        flash("{} is not enrolled".format(email), 'warning')
    else:
        try:
            Group.invite(current_user, invitee, assignment)
            success = "{} has been invited. They can accept the invite by logging into okpy.org".format(email)
            flash(success, "success")
        except BadRequest as e:
            flash(e.description, 'danger')
    return redirect(url_for('.assignment', course=course.offering, assign=assign))


@student.route(ASSIGNMENT_DETAIL + "group/remove/", methods=['POST'])
@login_required
@get_course
def group_remove(course, assign):
    assignment = Assignment.by_name(assign, course.offering)
    if not assignment:
        abort(404)

    target = User.lookup(request.form['email'])
    group = Group.lookup(current_user, assignment)
    if not target:
        flash("{} is not enrolled".format(request.form['email']), 'warning')
    elif not group:
        flash("You are not in a group", 'warning')
    else:
        try:
            group.remove(current_user, target)
        except BadRequest as e:
            flash(e.description, 'danger')

    return redirect(url_for('.assignment', course=course.offering, assign=assign))

@student.route(ASSIGNMENT_DETAIL + "group/respond/", methods=['POST'])
@login_required
@get_course
def group_respond(course, assign):
    assignment = Assignment.by_name(assign, course.offering)
    if not assignment:
        abort(404)

    action = request.form.get('action', None)
    if not action or action not in ['accept', 'decline']:
        abort(400)
    group = Group.lookup(current_user, assignment)
    if not group:
        flash("You are not in a group")
    else:
        try:
            if action == "accept":
                group.accept(current_user)
            else:
                group.decline(current_user)
        except BadRequest as e:
            flash(e.description, 'warning')

    return redirect(url_for('.assignment', course=course.offering, assign=assign))
