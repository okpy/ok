from flask import Blueprint, render_template, flash, request, redirect, \
    url_for, session,  current_app, abort
from flask.ext.login import login_user, logout_user, login_required, \
    current_user

import functools

from server.constants import VALID_ROLES, STAFF_ROLES, STUDENT_ROLE
from server.extensions import cache
from server.models import User, Course, Assignment, Group, Backup, Diff, db
from server.utils import generate_diff

student = Blueprint('student', __name__)


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
    # TODO : Should consider group submissions as well.
    user_id = current_user.id
    assignments = {
        'active': [(a, a.submission_time(user_id), a.group(user_id)) \
                        for a in course.assignments if a.active],
        'inactive': [(a, a.submission_time(user_id), a.group(user_id)) \
                            for a in course.assignments if not a.active]
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
        group = Group.lookup(current_user, assgn)
        if group:
            # usr_ids = [u.id for u in group.users()]
            # TODO : Fetch backups from group.
            pass
        backups = assgn.backups(current_user.id).limit(5).all()
        subms = assgn.submissions(current_user.id).limit(5).all()
        flagged = any([s.flagged for s in subms])
        print(flagged)
        return render_template('student/assignment/index.html', course=course,
                assignment=assgn, backups=backups, subms=subms, flagged=flagged)
    else:
        # flash("That assignment does not exist", "warning")
        abort(404)

@student.route("/course/<int:cid>/assignment/<int:aid>/<int:bid>")
@login_required
@is_enrolled
def code(cid, aid, bid):
    assgn = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if assgn:
        course = assgn.course
        group = Group.lookup(current_user, assgn)
        backup = Backup.query.get(bid)
        if backup and backup.can_view(current_user, group, assgn):
            submitter = User.query.get(backup.submitter)
            file_contents = [m for m in backup.messages
                             if m.kind == "file_contents"]
            if not file_contents:
                flash("That code submission doesn't contain any code")
                abort(404)

            template_files = assgn.template
            student_files = file_contents[0].contents
            student_files.pop('submit', None)

            if template_files is None:
                # Only render a diff for assignments with templates
                student_code = {k: v.split('\n') for k, v in student_files.iteritems()}
                return render_template('student/assignment/code_nodiff.html',
                                       course=course, assignment=assgn,
                                       backup=backup, submitter=submitter,
                                       diffs=student_code)

            diff = Diff.query.filter_by(assignment=aid, backup=bid).one_or_none()
            if diff is None:
                diff = Diff(assignment=aid, backup=bid)
                diff.diff = generate_diff(template_files, student_files)
                # db.session.add(diff)
                # db.session.commit()

            return render_template('student/assignment/code_diff.html',
                                    course=course, assignment=assgn,
                                    backup=backup, submitter=submitter,
                                    diffs=diff.diff)

        else:
            flash("That code doesn't exist (or you don't have permission)", "danger")
            abort(403)
    else:
        flash("That assignment does not exist", "danger")

    abort(404)
