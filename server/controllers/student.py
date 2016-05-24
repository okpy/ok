from flask import Blueprint, render_template, flash, request, redirect, \
    url_for, session,  current_app, abort, make_response
from flask.ext.login import login_user, logout_user, login_required, \
    current_user
from werkzeug.exceptions import BadRequest

import collections
import functools

from server import highlight, models, utils
from server.constants import VALID_ROLES, STAFF_ROLES, STUDENT_ROLE
from server.extensions import cache
from server.forms import CSRFForm
from server.models import User, Course, Assignment, Group, Backup, db
from server.utils import is_safe_redirect_url, group_action_email, \
    invite_email, send_email

student = Blueprint('student', __name__)

def check_enrollment(course):
    enrolled = current_user.is_enrolled(course.id)
    if not enrolled and not current_user.is_admin:
        flash("You have not been added to this course on OK", "warning")

def get_course(offering):
    """Get a course with the given name. If the user is not enrolled, flash
    a warning message.
    """
    course = Course.by_name(offering)
    if not course:
        abort(404)
    check_enrollment(course)
    return course

def get_assignment(name):
    """Get an assignment with the given name. If the user is not enrolled, flash
    a warning message.
    """
    assignment = Assignment.by_name(name)
    if not assignment:
        abort(404)
    check_enrollment(assignment.course)
    return assignment

@student.route('/')
def index():
    if current_user.is_authenticated:
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
        return render_template('student/courses/index.html', **courses)
    else:
        return render_template('index.html')

@student.route('/<offering:offering>/')
@login_required
def course(offering):
    course = get_course(offering)
    def assignment_info(assignment):
        # TODO does this make O(n) db queries?
        # TODO need group info too
        user_ids = assignment.active_user_ids(current_user.id)
        final_submission = assignment.final_submission(user_ids)
        submission_time = final_submission and final_submission.created
        group = Group.lookup(current_user, assignment)
        return assignment, submission_time, group

    assignments = {
        'active': [assignment_info(a) for a in course.assignments if a.active],
        'inactive': [assignment_info(a) for a in course.assignments if not a.active]
    }
    return render_template('student/course/index.html', course=course,
                           **assignments)

@student.route('/<assignment_name:name>/')
@login_required
def assignment(name):
    assign = get_assignment(name)
    user_ids = assign.active_user_ids(current_user.id)
    fs = assign.final_submission(user_ids)
    group = Group.lookup(current_user, assign)
    can_invite = assign.max_group_size > 1
    can_remove = group and group.has_status(current_user, 'active')

    if group:
        can_invite = len(group.members) < assign.max_group_size

    data = {
        'course': assign.course,
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

@student.route('/<assignment_name:name>/<bool(backups, submissions):submit>/')
@login_required
def list_backups(name, submit):
    assign = get_assignment(name)
    page = request.args.get('page', 1, type=int)
    user_ids = assign.active_user_ids(current_user.id)
    csrf_form = CSRFForm()

    if submit:
        backups = assign.submissions(user_ids)
    else:
        backups = assign.backups(user_ids)
    paginate = backups.paginate(page=page, per_page=10)
    return render_template('student/assignment/list.html', course=assign.course,
            assignment=assign, paginate=paginate, submit=submit, csrf_form=csrf_form)

@student.route('/<assignment_name:name>/<bool(backups, submissions):submit>/<hashid:bid>/')
@login_required
def code(name, submit, bid):
    assign = get_assignment(name)
    user_ids = assign.active_user_ids(current_user.id)
    backup = Backup.query.get(bid)
    if not (backup and backup.submit == submit and backup.can_view(current_user, user_ids, assign.course)):
        abort(404)
    diff_type = request.args.get('diff', None)
    if diff_type not in (None, 'short', 'full'):
        return redirect(url_for('.code', name=name, submit=submit, bid=bid))
    if not assign.files and diff_type:
        return abort(404)
    # sort comments by (filename, line)
    comments = collections.defaultdict(list)
    for comment in backup.comments:
        comments[(comment.filename, comment.line)].append(comment)
    # highlight files and add comments
    files = highlight.diff_files(assign.files, backup.files(), diff_type)
    for filename, lines in files.items():
        for line in lines:
            line.comments = comments[(filename, line.line_after)]
    return render_template('student/assignment/code.html',
        course=assign.course, assignment=assign, backup=backup,
        files=files, diff_type=diff_type)

@student.route('/<assignment_name:name>/<bool(backups, submissions):submit>/<hashid:bid>/download/<file>')
@login_required
def download(name, submit, bid, file):
    backup = Backup.query.get(bid)
    assign = get_assignment(name)
    user_ids = assign.active_user_ids(current_user.id)
    if not (backup and backup.submit == submit and backup.can_view(current_user, user_ids, assign.course)):
        abort(404)
    try:
        contents = backup.files()[file]
    except KeyError:
        abort(404)
    response = make_response(contents)
    response.headers["Content-Disposition"] = "attachment; filename=%s" % file
    return response

@student.route('/<assignment_name:name>/submissions/<hashid:bid>/flag/', methods=['POST'])
@login_required
def flag(name, bid):
    assign = get_assignment(name)
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

@student.route('/<assignment_name:name>/group/invite/', methods=['POST'])
@login_required
def group_invite(name):
    assignment = get_assignment(name)
    email = request.form['email']
    invitee = User.lookup(email)
    if not invitee:
        flash("{} is not enrolled".format(email), 'warning')
    else:
        try:
            Group.invite(current_user, invitee, assignment)
            success = "{} has been invited. They can accept the invite by logging into okpy.org".format(email)
            invite_email(current_user, invitee, assignment)
            flash(success, "success")
        except BadRequest as e:
            flash(e.description, 'danger')
    return redirect(url_for('.assignment', name=assignment.name))


@student.route('/<assignment_name:name>/group/remove/', methods=['POST'])
@login_required
def group_remove(name):
    assignment = get_assignment(name)
    target = User.lookup(request.form['email'])
    group = Group.lookup(current_user, assignment)
    if not target:
        flash("{} is not enrolled".format(request.form['email']), 'warning')
    elif not group:
        flash("You are not in a group", 'warning')
    else:
        try:
            members = [m.user.email for m in group.members]
            group.remove(current_user, target)
            subject = "{} has been removed from your group".format(target.email)
            body = "{} removed {} from the group.".format(current_user.email, target.email)
            res = send_email(members, subject, body)
        except BadRequest as e:
            flash(e.description, 'danger')
    return redirect(url_for('.assignment', name=assignment.name))

@student.route('/<assignment_name:name>/group/respond/', methods=['POST'])
@login_required
def group_respond(name):
    assignment = get_assignment(name)
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
                subject = "{} has accepted your invitation".format(current_user.email)
                body = "Your group now has {} members".format(len(group.members))
                group_action_email(group.members, subject, body)
            else:
                members = [m.user.email for m in group.members]
                group.decline(current_user)
                subject = "{} has declined your invitation".format(current_user.email)
                send_email(members, subject, subject)

        except BadRequest as e:
            flash(e.description, 'danger')
    return redirect(url_for('.assignment', name=assignment.name))

@student.route('/comments/', methods=['POST'])
@login_required
def new_comment():
    comment = models.Comment(
        backup_id=utils.decode_id(request.form['backup_id']),
        author_id=current_user.id,
        filename=request.form['filename'],
        line=request.form.get('line', type=int),
        message=request.form['message'])
    db.session.add(comment)
    db.session.commit()
    return render_template('student/assignment/comment.html', comment=comment)

@student.route('/comments/<hashid:comment_id>', methods=['PUT', 'DELETE'])
@login_required
def edit_comment(comment_id):
    comment = models.Comment.query.get(comment_id)
    if not comment or comment.author != current_user:
        abort(404)
    if request.method == 'DELETE':
        db.session.delete(comment)
        db.session.commit()
        return ('', 204)
    else:
        comment.message = request.form['message']
        db.session.commit()
        return render_template('student/assignment/comment.html', comment=comment)
