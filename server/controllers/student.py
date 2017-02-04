from flask import (Blueprint, render_template, flash, request, redirect,
                   url_for, abort, make_response, jsonify)
from flask_login import login_required, current_user
from werkzeug.exceptions import BadRequest

import collections
import logging
import os
import time

from server import highlight, models, utils
from server.autograder import submit_continous
from server.constants import VALID_ROLES, STAFF_ROLES, STUDENT_ROLE, MAX_UPLOAD_FILE_SIZE
from server.forms import CSRFForm, UploadSubmissionForm
from server.models import User, Course, Assignment, Group, Backup, Message, ExternalFile, db
from server.utils import (is_safe_redirect_url, group_action_email,
                          invite_email, send_email)

logger = logging.getLogger(__name__)

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
        displayed_courses = courses['current'] + courses['past']
        courses['all'] = [c for c in all_courses if c not in displayed_courses]
        return render_template('student/courses/index.html', **courses)
    else:
        return render_template('index.html')


@student.route('/<offering:offering>/')
@login_required
def course(offering):
    course = get_course(offering)
    assignments = {
        'active': [a.user_status(current_user) for a in course.assignments
                   if a.active and a.visible],
        'inactive': [a.user_status(current_user) for a in course.assignments
                     if not a.active and a.visible]
    }
    return render_template('student/course/index.html', course=course,
                           **assignments)


@student.route('/<assignment_name:name>/')
@login_required
def assignment(name):
    assign = get_assignment(name)
    user_ids = assign.active_user_ids(current_user.id)
    fs = assign.final_submission(user_ids)
    revision = assign.revision(user_ids)
    scores = assign.scores(user_ids)

    group = Group.lookup(current_user, assign)
    can_invite = assign.max_group_size > 1 and assign.active
    can_remove = group and group.has_status(current_user, 'active')

    if group:
        can_invite = len(group.members) < assign.max_group_size

    data = {
        'course': assign.course,
        'assignment': assign,
        'backups': assign.backups(user_ids).limit(5).all(),
        'subms': assign.submissions(user_ids).limit(5).all(),
        'final_submission': fs,
        'flagged': fs and fs.flagged,
        'group': group,
        'revision': revision,
        'scores': scores,
        'can_invite': can_invite,
        'can_remove': can_remove,
        'csrf_form': CSRFForm()
    }
    return render_template('student/assignment/index.html', **data)


@student.route('/<assignment_name:name>/submit', methods=['GET', 'POST'])
@login_required
def submit_assignment(name):
    assign = get_assignment(name)
    group = Group.lookup(current_user, assign)
    user_ids = assign.active_user_ids(current_user.id)
    fs = assign.final_submission(user_ids)
    if not assign.uploads_enabled:
        flash("This assignment cannot be submitted online", 'warning')
        return redirect(url_for('.assignment', name=assign.name))
    if not assign.active:
        flash("It's too late to submit this assignment", 'warning')
        return redirect(url_for('.assignment', name=assign.name))


    if request.method == "POST":
        backup = Backup(
            submitter=current_user,
            assignment=assign,
            submit=True,
        )
        assignment = backup.assignment
        templates = assignment.files or []

        files = {}

        def extract_file_index(file_ind):
            """ Get the index of of file objects. Used because
            request.files.getlist() does not handle uniquely indexed
            lists.
            >>> extract_file_index('file[12'])
            12
            """
            brace_loc = file_ind.find('[')
            index_str = file_ind[brace_loc+1:-1]
            return int(index_str)


        # A list of one element lists
        sorted_uploads = sorted(list(request.files.items()),
                                key=lambda x: extract_file_index(x[0]))
        uploads = [v[1] for v in sorted_uploads]
        full_path_names = list(request.form.listvalues())[0]

        template_files = assign.files or []
        file_names = [os.path.split(f)[1] for f in full_path_names]
        missing = [t for t in template_files if t not in file_names]
        if missing:
            return jsonify({
                'error': ('Missing files: {}. The following files are required: {}'
                          .format(', '.join(missing), ', '.join(template_files)))
            }), 400

        backup_folder_postfix = time.time()

        for full_path, upload in zip(full_path_names, uploads):
            data = upload.read()
            if len(data) > MAX_UPLOAD_FILE_SIZE:  # file is too large (over 15 MB)
                return jsonify({
                  'error': ('{} is larger than the maximum file size of {}MB'
                            .format(full_path, MAX_UPLOAD_FILE_SIZE))
                }), 400
            try:
                files[full_path] = str(data, 'utf-8')
            except UnicodeDecodeError:
                upload.stream.seek(0) # We've already read data, so reset before uploading
                dest_folder = "uploads/{}/{}/{}/".format(assign.name, current_user.id, backup_folder_postfix)
                bin_file = ExternalFile.upload(upload.stream, current_user.id, full_path,
                                               prefix=dest_folder, course_id=assign.course.id,
                                               backup=backup, assignment_id=assign.id)
                db.session.add(bin_file)

        message = Message(kind='file_contents', contents=files)
        backup.messages.append(message)

        db.session.add(backup)
        db.session.commit()
        return jsonify({
            'backup': backup.hashid,
            'url': url_for('.code', name=assign.name, submit=backup.submit,
                           bid=backup.id)
        })

    return render_template('student/assignment/submit.html', assignment=assign,
                           group=group, course=assign.course)


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
                           assignment=assign, paginate=paginate, submit=submit,
                           csrf_form=csrf_form)

@student.route('/<assignment_name:name>/<bool(backups, submissions):submit>/<hashid:bid>/')
@login_required
def code(name, submit, bid):
    assign = get_assignment(name)
    backup = Backup.query.get(bid)

    if not (backup and Backup.can(backup, current_user, "view")):
        abort(404)
    if backup.submit != submit:
        return redirect(url_for('.code', name=name, submit=backup.submit, bid=bid))

    diff_type = request.args.get('diff')
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
    for filename, source_file in files.items():
        for line in source_file.lines:
            line.comments = comments[(filename, line.line_after)]

    for filename, ex_file in backup.external_files_dict().items():
        files[filename] = ex_file

    return render_template('student/assignment/code.html',
        course=assign.course, assignment=assign, backup=backup,
        files=files, diff_type=diff_type)


@student.route('/<assignment_name:name>/<bool(backups, submissions):submit>/'
               '<hashid:bid>/download/<path:file>')
@login_required
def download(name, submit, bid, file):
    backup = Backup.query.get(bid)
    if not (backup and Backup.can(backup, current_user, "view")):
        abort(404)
    if backup.submit != submit:
        return redirect(url_for('.download', name=name, submit=backup.submit,
                                bid=bid, file=file))
    try:
        contents = backup.files()[file]
    except KeyError:
        abort(404)
    response = make_response(contents)

    content_disposition = "inline" if 'raw' in request.args else "attachment"
    response.headers["Content-Disposition"] = ("{0}; filename={1!s}"
                                               .format(content_disposition, file))
    response.headers["Content-Security-Policy"] = "default-src 'none';"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Type"] = "text/plain; charset=UTF-8"

    return response

@student.route('/<assignment_name:name>/submissions/<hashid:bid>/flag/',
               methods=['POST'])
@login_required
def flag(name, bid):
    assign = get_assignment(name)
    user_ids = assign.active_user_ids(current_user.id)
    flag = 'flag' in request.form
    next_url = request.form['next']

    backup = models.Backup.query.get(bid)
    if not Backup.can(backup, current_user, "view"):
        abort(404)

    if not assign.active:
        flash('It is too late to change what submission is graded.', 'warning')
    elif flag:
        result = assign.flag(bid, user_ids)
        flash('Flagged submission {}. '.format(result.hashid) +
              'This submission will be used for grading', 'success')
    else:
        result = assign.unflag(bid, user_ids)
        flash('Removed flag from {}. '.format(result.hashid) +
              'The most recent submission will be used for grading.', 'success')

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
        flash("{0} is not enrolled".format(email), 'warning')
    else:
        try:
            Group.invite(current_user, invitee, assignment)
            success = "{0} has been invited. They can accept the invite by logging into okpy.org".format(email)
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
        flash("{0} is not enrolled".format(request.form['email']), 'warning')
    elif not group:
        flash("You are not in a group", 'warning')
    else:
        try:
            members = [m.user.email for m in group.members]
            group.remove(current_user, target)
            subject = "{0} has been removed from your {1} group".format(target.email,
                                                                        assignment.display_name)
            if target.email == current_user.email:
                descriptor = "themselves"
            else:
                descriptor = target.email
            body = "{0} removed {1} from the group.".format(current_user.email, descriptor)
            send_email(members, subject, body)
        except BadRequest as e:
            flash(e.description, 'danger')
    return redirect(url_for('.assignment', name=assignment.name))


@student.route('/<assignment_name:name>/group/respond/', methods=['POST'])
@login_required
def group_respond(name):
    assignment = get_assignment(name)
    action = request.form.get('action')
    target = request.form.get('email')
    if not action or action not in ['accept', 'decline', 'revoke']:
        abort(400)
    group = Group.lookup(current_user, assignment)
    if not group:
        flash("You are not in a group")
    else:
        try:

            if action == "accept":
                group.accept(current_user)
                subject = "{0} has accepted the invitation to join your group".format(current_user.email)
                body = "Your group for {0} now has {1} members".format(assignment.display_name,
                                                                       len(group.members))
                group_action_email(group.members, subject, body)
            elif action == "decline":
                members = [m.user.email for m in group.members]
                group.decline(current_user)
                subject = "{0} declined an invite to join the group".format(current_user.email)
                body = "{0} declined to join the group for {1}".format(current_user.email,
                                                                       assignment.display_name)
                send_email(members, subject, body)
            elif action == "revoke":
                members = [m.user.email for m in group.members]
                group.decline(current_user)
                subject = "{0} invitation for {1} revoked".format(assignment.display_name,
                                                                  target)
                body = "{0} has revoked the invitation for {1}".format(current_user.email,
                                                                       target)
                send_email(members, subject, body)

        except BadRequest as e:
            flash(e.description, 'danger')
    return redirect(url_for('.assignment', name=assignment.name))


@student.route('/comments/', methods=['POST'])
@login_required
def new_comment():
    if not models.Comment.can(None, current_user, "create"):
        abort(403)

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
    if not models.Comment.can(comment, current_user, "edit"):
        abort(403)

    if request.method == 'DELETE':
        db.session.delete(comment)
        db.session.commit()
        return ('', 204)
    else:
        comment.message = request.form['message']
        db.session.commit()
        return render_template('student/assignment/comment.html', comment=comment)
