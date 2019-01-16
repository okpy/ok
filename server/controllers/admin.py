import collections
import csv
import datetime as dt
import copy

from functools import wraps
from io import StringIO

from flask import (Blueprint, render_template, flash, redirect, Response,
                   url_for, abort, request, stream_with_context)
from werkzeug.exceptions import BadRequest

from flask_login import current_user, login_required
import pygal
from pygal.style import CleanStyle
import requests.exceptions

from server import autograder

import server.controllers.api as ok_api
from server.models import (User, Course, Assignment, Enrollment, Version,
                           GradingTask, Backup, Score, Group, Client, Job,
                           Message, CanvasCourse, CanvasAssignment, MossResult,
                           Extension, db)
from server.contrib import analyze

from server.constants import (EMAIL_FORMAT, INSTRUCTOR_ROLE, STAFF_ROLES, STUDENT_ROLE,
                              LAB_ASSISTANT_ROLE, SCORE_KINDS, AUTOGRADER_URL)
import server.canvas.api as canvas_api
import server.canvas.jobs
from server.extensions import cache
import server.forms as forms
import server.jobs as jobs
from server.jobs import (example, export, moss, scores_audit, github_search,
                         scores_notify, checkpoint, effort, upload_scores,
                        export_grades)

import server.highlight as highlight
import server.utils as utils

admin = Blueprint('admin', __name__)

def is_staff(course_arg=None):
    """ A decorator for routes to ensure that user is a member of
    the course staff.

    Usage:
    @is_staff() - A staff member for any course
    @is_staff(course_arg=1) A staff member for the course with id 1
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated:
                if current_user.is_admin:
                    return func(*args, **kwargs)
                roles = current_user.enrollments(roles=STAFF_ROLES)
                if len(roles) > 0:
                    if course_arg:
                        course = kwargs[course_arg]
                        if course in [r.course.id for r in roles]:
                            return func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
            else:
                return redirect(url_for("student.index"))
            flash("You are not on the course staff", "warning")
            return redirect(url_for("student.index"))
        return login_required(wrapper)
    return decorator

def is_admin():
    """ A decorator for routes to ensure the user is an admin."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated and current_user.is_admin:
                return func(*args, **kwargs)
            else:
                flash("You are not an administrator", "warning")
                return redirect(url_for("admin.index"))
        return login_required(wrapper)
    return decorator

def is_oauth_client_owner(oauth_client_id_arg):
    """ A decorator for OAuth client management routes to ensure the user owns
        the OAuth client or is an admin."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated:
                if current_user.is_admin:
                    return func(*args, **kwargs)
                oauth_client_id = kwargs[oauth_client_id_arg]
                clients = Client.query.filter_by(user_id=current_user.id)
                if clients.count() > 0:
                    if oauth_client_id in [c.client_id for c in clients]:
                        return func(*args, **kwargs)
            flash("You do not have access to this OAuth client", "warning")
            return redirect(url_for("admin.clients"))
        return login_required(wrapper)
    return decorator

@admin.context_processor
@cache.memoize(1800)
def inject_pending_oauth_clients():
    """ Injects an additional template variable used to display the notification
        indicator of pending OAuth clients to admins."""
    num_pending_oauth_clients = Client.query.filter_by(active=False).count()
    return dict(num_pending_oauth_clients=num_pending_oauth_clients)

def get_courses(cid=None):
    if current_user.is_authenticated and current_user.is_admin:
        courses = (Course.query.order_by(Course.created.desc())
                         .all())
    else:
        enrollments = current_user.enrollments(roles=STAFF_ROLES)
        courses = [e.course for e in enrollments]
    if not cid:
        return courses, []

    matching_courses = [c for c in courses if c.id == cid]
    if len(matching_courses) == 0:
        abort(401)
    current_course = matching_courses[0]
    return courses, current_course


@admin.route("/")
@is_staff()
def index():
    courses, current_course = get_courses()
    if courses and not current_user.is_admin:
        return redirect(url_for(".course_assignments", cid=courses[0].id))
    return redirect(url_for(".list_courses"))

@admin.route('/grading')
@is_staff()
def grading_tasks(username=None):
    courses, current_course = get_courses()
    page = request.args.get('page', 1, type=int)
    tasks_query = GradingTask.query.filter_by(grader=current_user)
    queue = (tasks_query.options(db.joinedload('assignment'))
                        .order_by(GradingTask.score_id.asc())
                        .order_by(GradingTask.created.asc())
                        .paginate(page=page, per_page=20))

    remaining = tasks_query.filter_by(score_id=None).count()
    percent_left = (1-(remaining/max(1, queue.total))) * 100
    return render_template('staff/grading/queue.html', courses=courses,
                           queue=queue, remaining=remaining,
                           percent_left=percent_left)

def grading_view(backup, form=None, is_composition=False):
    """ General purpose grading view. Used by routes."""
    courses, current_course = get_courses()
    assign = backup.assignment
    diff_type = request.args.get('diff')
    if diff_type not in (None, 'short', 'full'):
        diff_type = None
    if not assign.files and diff_type:
        diff_type = None

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

    group = [User.query.get(o) for o in backup.owners()]
    task = backup.grading_tasks
    if task:
        # Choose the first grading_task
        task = task[0]

    return render_template('staff/grading/code.html', courses=courses, assignment=assign,
                           backup=backup, group=group, files=files, diff_type=diff_type,
                           task=task, form=form, is_composition=is_composition)

@admin.route('/grading/<hashid:bid>')
@is_staff()
def grading(bid):
    backup = Backup.query.get(bid)
    if not (backup and Backup.can(backup, current_user, "grade")):
        abort(404)

    form = forms.GradeForm()
    existing = [s for s in backup.scores if not s.archived]
    first_score = existing[0] if existing else None

    if first_score and first_score.kind in SCORE_KINDS:
        form = forms.GradeForm(kind=first_score.kind)
        form.kind.data = first_score.kind
        form.message.data = first_score.message
        form.score.data = first_score.score

    return grading_view(backup, form=form)

@admin.route('/composition/<hashid:bid>')
@is_staff()
def composition(bid):
    backup = Backup.query.get(bid)
    if not (backup and Backup.can(backup, current_user, "grade")):
        abort(404)
    form = forms.CompositionScoreForm()
    existing = Score.query.filter_by(backup=backup, kind="composition").first()
    if existing:
        form.kind.data = "composition"
        form.message.data = existing.message
        form.score.data = existing.score
    return grading_view(backup, form=form, is_composition=True)

@admin.route('/grading/<hashid:bid>/edit', methods=['GET', 'POST'])
@is_staff()
def edit_backup(bid):
    courses, current_course = get_courses()
    backup = Backup.query.options(db.joinedload('assignment')).get(bid)
    if not backup:
        abort(404)
    if not Backup.can(backup, current_user, 'grade'):
        flash("You do not have permission to score this assignment.", "warning")
        abort(401)
    form = forms.SubmissionTimeForm()
    if form.validate_on_submit():
        backup.custom_submission_time = form.get_submission_time(backup.assignment)
        db.session.commit()
        flash('Submission time saved', 'success')
        return redirect(url_for('.edit_backup', bid=bid))
    else:
        form.set_submission_time(backup)
    return render_template(
        'staff/grading/edit.html',
        courses=courses,
        current_course=current_course,
        backup=backup,
        student=backup.submitter,
        form=form,
    )

@admin.route('/grading/<hashid:bid>/grade', methods=['POST'])
@is_staff()
def grade(bid):
    """ Used as a form submission endpoint. """
    backup = Backup.query.options(db.joinedload('assignment')).get(bid)
    if not backup:
        abort(404)
    if not Backup.can(backup, current_user, 'grade'):
        flash("You do not have permission to score this assignment.", "warning")
        abort(401)

    form = forms.GradeForm()
    score_kind = form.kind.data.strip().lower()
    is_composition = (score_kind == "composition")
    # TODO: Form should include redirect url instead of guessing based off tag

    if is_composition:
        form = forms.CompositionScoreForm()

    if not form.validate_on_submit():
        return grading_view(backup, form=form)

    score = Score(backup=backup, grader=current_user,
                  assignment_id=backup.assignment_id, user_id=backup.submitter_id)
    form.populate_obj(score)
    db.session.add(score)
    db.session.commit()

    # Archive old scores of the same kind
    score.archive_duplicates()

    next_page = None
    flash_msg = "Added a {0} {1} score.".format(score.score, score_kind)

    # Find GradingTasks applicable to this score
    tasks = backup.grading_tasks
    for task in tasks:
        task.score = score
        cache.delete_memoized(User.num_grading_tasks, task.grader)

    db.session.commit()

    if len(tasks) == 1:
        # Go to next task for the current task queue if possible.
        task = tasks[0]
        next_task = task.get_next_task()
        next_route = '.composition' if is_composition else '.grading'
        # Handle case when the task is on the users queue
        if next_task:
            flash_msg += (" There are {0} tasks left. Here's the next submission:"
                          .format(task.remaining))
            next_page = url_for(next_route, bid=next_task.backup_id)
        else:
            flash_msg += " All done with grading for {}".format(backup.assignment.name)
            next_page = url_for('.grading_tasks')
    else:
        # TODO: Send task id or redirect_url in the grading form
        # For now, default to grading tasks
        next_page = url_for('.grading_tasks')

    flash(flash_msg, 'success')

    if not next_page:
        next_page = url_for('.assignment_queues', aid=backup.assignment_id,
                            cid=backup.assignment.course_id)
    return redirect(next_page)

@admin.route('/grading/<hashid:bid>/autograde', methods=['POST'])
@is_staff()
def autograde_backup(bid):
    backup = Backup.query.options(db.joinedload('assignment')).get(bid)
    if not backup:
        abort(404)
    if not Backup.can(backup, current_user, 'grade'):
        flash("You do not have permission to score this assignment.", "warning")
        abort(401)

    form = forms.CSRFForm()
    if form.validate_on_submit():
        try:
            token = autograder.create_autograder_token(current_user.id)
            autograder.autograde_backup(token, backup.assignment, backup.id)
            flash('Submitted to the autograder', 'success')
        except ValueError as e:
            flash(str(e), 'error')
    return redirect(url_for('.grading', bid=bid))

@admin.route("/versions/<name>", methods=['GET', 'POST'])
@is_admin()
def client_version(name):
    courses, current_course = get_courses()

    version = Version.query.filter_by(name=name).one_or_none()
    if not version:
        version = Version(name=name)
    form = forms.VersionForm(obj=version)
    if form.validate_on_submit():
        form.populate_obj(version)
        version.save()
        flash(name + " version updated successfully.", "success")
        return redirect(url_for(".client_version", name=name))

    return render_template('staff/client_version.html',
                           courses=courses, current_course=current_course,
                           version=version, form=form)

##########
# Course #
##########
@admin.route("/course/")
@is_staff()
def list_courses():
    courses, current_course = get_courses()
    active_courses = [c for c in courses if c.active]
    inactive_courses = [c for c in courses if not c.active]
    other_courses = [c for c in Course.query.all() if c not in courses]

    return render_template('staff/course/course.list.html',
    current_course=current_course, courses=courses,
                           active_courses=active_courses,
                           inactive_courses=inactive_courses,
                           other_courses=other_courses)

@admin.route("/course/new", methods=['GET', 'POST'])
@login_required
def create_course():
    courses, current_course = get_courses()
    form = forms.NewCourseForm()
    if form.validate_on_submit():
        new_course = Course()
        form.populate_obj(new_course)

        db.session.add(new_course)
        # Add the user as an instructor, create a default assignment
        new_course.initialize_content(current_user)

        utils.new_course_email(current_user, new_course)

        flash(new_course.offering + " created successfully.", "success")
        return redirect(url_for(".course", cid=new_course.id))
    return render_template('staff/course/course.new.html', form=form,
                           courses=courses)

@admin.route("/course/<int:cid>")
@admin.route("/course/<int:cid>/")
@is_staff(course_arg='cid')
def course(cid):
    courses, current_course = get_courses(cid)

    students = (Enrollment.query
                          .options(db.joinedload('user'))
                          .filter(Enrollment.role == STUDENT_ROLE,
                                  Enrollment.course == current_course)
                            .all())
    needs_intro = len(students) < 5

    return render_template('staff/course/course.html', courses=courses,
                           students=students,
                           needs_intro=needs_intro,
                           stats=current_course.statistics(),
                           current_course=current_course)

@admin.route("/course/<int:cid>/grades/export", methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def export_grades_job(cid):
    courses, current_course = get_courses(cid)

    form = forms.ExportGradesForm(current_course.assignments)
    if form.validate_on_submit():
        job = jobs.enqueue_job(
            export_grades.export_grades,
            description="Export Grades for {}".format(current_course.offering),
            timeout=2 * 60 * 60, # 1 hour
            course_id=cid,
            result_kind='link',
            # no arguments
        )
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    return render_template('staff/jobs/export_grades.html', form=form,
                            courses=courses, course=current_course)

@admin.route("/course/<int:cid>/settings", methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def course_settings(cid):
    courses, current_course = get_courses(cid)
    form = forms.CourseUpdateForm(obj=current_course)
    if form.validate_on_submit():
        form.populate_obj(current_course)
        db.session.commit()

        flash(current_course.offering + " edited successfully.", "success")
        return redirect(url_for(".course", cid=current_course.id))
    return render_template('staff/course/course.edit.html', form=form,
                           courses=courses, current_course=current_course)

@admin.route("/course/<int:cid>/section/", methods=['GET', 'POST'])
@admin.route("/course/<int:cid>/section/<int:sctn_id>", methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def section_console(cid, sctn_id=None):
    courses, current_course = get_courses(cid)
    form = forms.SectionAssignmentForm()
    if form.validate_on_submit():
        email, role, section = form.email.data, form.role.data, form.section.data
        user = User.lookup(email)
        if user:
            record = Enrollment.query.filter_by(user_id=user.id,
                                                course_id=cid).one_or_none()
            if record:
                form.name.data = user.name
                form.sid.data = record.sid
                form.secondary.data = record.class_account
                form.role.data = record.role
                Enrollment.enroll_from_form(cid, form)
                flash("Changed {email} to Section {section}".format(
                    email=email, section=section), "success")
        else:
            flash("{email} is not enrolled as a {role}".format(
                email=email, role=role), "error")

    if sctn_id is None:
        staff_record = (Enrollment.query
                        .filter_by(user_id=current_user.id, course_id=cid)
                        .filter(Enrollment.role.in_(STAFF_ROLES))
                        .one_or_none())
        # Admins may not have any staff record, but can view enrollment
        # for all courses.
        sctn_id = staff_record.section if staff_record else None

    staff = (Enrollment.query
             .filter(Enrollment.role.in_(STAFF_ROLES),
                     Enrollment.course == current_course)
             .all())

    if sctn_id is not None:
        enrollments = (Enrollment.query
                       .filter(Enrollment.role.in_([STUDENT_ROLE]),
                               Enrollment.section == sctn_id,
                               Enrollment.course == current_course)
                       .all())
    else:
        enrollments = []

    student_emails = []
    for enrollment in enrollments:
        student_emails.append(EMAIL_FORMAT.format(
            name=enrollment.user.identifier,
            email=enrollment.user.email))

    student_emails_str = "\n".join(student_emails)

    return render_template(
        'staff/course/section/section.html',
        courses=courses, form=form, current_course=current_course,
        enrollments=enrollments, staff=staff, emails=student_emails_str)

@admin.route("/course/<int:cid>/assignments")
@is_staff(course_arg='cid')
def course_assignments(cid):
    courses, current_course = get_courses(cid)
    assgns = current_course.assignments
    active_asgns = [a for a in assgns if a.active]
    due_asgns = [a for a in assgns if not a.active]
    # TODO CLEANUP : Better way to send this data to the template.
    return render_template('staff/course/assignment/assignments.html',
                           courses=courses, current_course=current_course,
                           active_asgns=active_asgns, due_assgns=due_asgns)


@admin.route("/course/<int:cid>/assignments/new", methods=["GET", "POST"])
@is_staff(course_arg='cid')
def new_assignment(cid):
    courses, current_course = get_courses(cid)
    if not Assignment.can(None, current_user, 'create'):
        flash('Insufficient permissions', 'error')
        return abort(401)

    form = forms.AssignmentForm(course=current_course)
    if form.validate_on_submit():
        model = Assignment(course_id=cid, creator_id=current_user.id)
        form.populate_obj(model)
        db.session.add(model)
        db.session.commit()
        cache.delete_memoized(Assignment.name_to_assign_info)

        flash("Assignment created successfully.", "success")
        if form.visible.data:
            return redirect(url_for(".templates", cid=cid, aid=model.id))
        return redirect(url_for(".course_assignments", cid=cid))

    return render_template('staff/course/assignment/assignment.new.html', form=form,
                           courses=courses, current_course=current_course)

@admin.route("/course/<int:cid>/assignments/<int:aid>",
             methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def assignment(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign:
        return abort(404)
    if not Assignment.can(assign, current_user, 'edit'):
        flash('Insufficient permissions', 'error')
        return abort(401)

    form = forms.AssignmentUpdateForm(obj=assign, course=current_course)
    if form.validate_on_submit():
        # populate_obj converts back to UTC
        form.populate_obj(assign)
        assign.creator_id = current_user.id
        cache.delete_memoized(Assignment.name_to_assign_info)
        db.session.commit()
        flash("Assignment edited successfully.", "success")

    return render_template('staff/course/assignment/assignment.html', assignment=assign,
                           form=form, courses=courses, autograder_url=AUTOGRADER_URL,
                           current_course=current_course)

@admin.route("/course/<int:cid>/assignments/<int:aid>/stats")
@is_staff(course_arg='cid')
def assignment_stats(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not Assignment.can(assign, current_user, 'edit'):
        flash('Insufficient permissions', 'error')
        return abort(401)

    stats = Assignment.assignment_stats(assign.id)

    submissions = [d for d in stats.pop('raw_data')]

    pie_chart = pygal.Pie(half_pie=True, disable_xml_declaration=True,
                          style=CleanStyle,
                          inner_radius=.5, legend_at_bottom=True)
    pie_chart.title = 'Students submission status'
    pie_chart.add('Students with Submissions', stats['students_with_subm'])
    pie_chart.add('Students with Backups', stats['students_with_backup'])
    pie_chart.add('Not Started', stats['students_no_backup'])

    return render_template('staff/course/assignment/assignment.stats.html',
                           assignment=assign, subm_chart=pie_chart,
                           courses=courses, stats=stats, submissions=submissions,
                           current_course=current_course)

@admin.route("/course/<int:cid>/assignments/<int:aid>/template",
             methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def templates(cid, aid):
    courses, current_course = get_courses(cid)
    assignment = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not Assignment.can(assignment, current_user, 'edit'):
        flash('Insufficient permissions', 'error')
        return abort(401)

    form = forms.AssignmentTemplateForm()

    if assignment.course != current_course:
        return abort(401)

    if form.validate_on_submit():
        files = request.files.getlist("template_files")
        if files:
            templates = {}
            for template in files:
                try:
                    templates[template.filename] = str(template.read(), 'utf-8')
                except UnicodeDecodeError:
                    flash(
                        '{} is not a UTF-8 text file and was '
                        'not uploaded'.format(template.filename), 'warning')
            assignment.files = templates
        cache.delete_memoized(Assignment.name_to_assign_info)
        db.session.commit()
        flash("Templates Uploaded", "success")

    # TODO: Use same student facing code rendering/highlighting
    return render_template('staff/course/assignment/assignment.template.html',
                           assignment=assignment, form=form, courses=courses,
                           current_course=current_course)

@admin.route("/course/<int:cid>/assignments/<int:aid>/publish",
                methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def publish_scores(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not Assignment.can(assign, current_user, 'publish_scores'):
        flash('Insufficient permissions', 'error')
        abort(401)

    form = forms.PublishScores(obj=assign)
    if form.validate_on_submit():
        assign.published_scores = form.published_scores.data
        db.session.commit()
        flash(
            "Saved published scores for {}".format(assign.display_name),
            "success",
        )
        return redirect(url_for('.publish_scores', cid=cid, aid=aid))
    return render_template('staff/course/assignment/assignment.publish.html',
                            assignment=assign, form=form, courses=courses,
                            current_course=current_course)

##########
# Scores #
##########

@admin.route("/course/<int:cid>/assignments/<int:aid>/scores")
@is_staff(course_arg='cid')
def view_scores(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not Assignment.can(assign, current_user, 'export'):
        flash('Insufficient permissions', 'error')
        return abort(401)

    include_all = request.args.get('all', False, type=bool)
    query = (Score.query.options(db.joinedload('backup'), db.joinedload(Score.grader))
                        .filter_by(assignment=assign))

    if not include_all:
        query = query.filter_by(archived=False)

    # sort scores by submission time in descending order, to match front end display
    query = query.order_by(Score.created.desc())

    all_scores = query.all()

    score_distribution = collections.defaultdict(list)
    for score in all_scores:
        score_distribution[score.kind].append(score.score)

    bar_charts = collections.OrderedDict()
    sorted_kinds = sorted(score_distribution, reverse=True,
                          key=lambda x: len(score_distribution[x]))
    for kind in sorted_kinds:
        score_values = score_distribution[kind]
        score_counts = collections.Counter(score_values)
        bar_chart = pygal.Bar(show_legend=False, x_labels_major_count=6, margin=0,
                              height=400, show_minor_x_labels=False, truncate_label=5)
        bar_chart.fill = True
        bar_chart.title = '{} distribution ({} items)'.format(kind, len(score_values))
        bar_chart.add(kind, [score_counts.get(x) for x in sorted(score_counts)])
        bar_chart.x_labels = [x for x in sorted(score_counts)]

        bar_charts[kind] = bar_chart.render().decode("utf-8")

    return render_template('staff/course/assignment/assignment.scores.html',
                           autograder_url=AUTOGRADER_URL,
                           assignment=assign, current_course=current_course,
                           courses=courses, scores=all_scores,
                           score_plots=bar_charts)

@admin.route("/course/<int:cid>/assignments/<int:aid>/scores/audit")
@is_staff(course_arg='cid')
def audit_scores(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not Assignment.can(assign, current_user, 'export'):
        flash('Insufficient permissions', 'error')
        return abort(401)
    job = jobs.enqueue_job(scores_audit.audit_missing_scores,
                           course_id=current_course.id,
                           description='Missing scores audit for {}'.format(assign.display_name),
                           assign_id=assign.id)
    return redirect(url_for('.course_job', cid=cid, job_id=job.id))

@admin.route("/course/<int:cid>/assignments/<int:aid>/scores/notify",
             methods=["GET", "POST"])
@is_staff(course_arg='cid')
def send_scores_job(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    form = forms.EmailScoresForm()
    if form.validate_on_submit():

        for kind in form.kinds.data:
            if kind not in assign.published_scores:
                flash(("{0} scores are not visible to students. Please publish "
                            " those scores and try again").format(kind.title()),
                      'error')

                return render_template(
                    'staff/jobs/notify_scores.html',
                    courses=courses,
                    current_course=current_course,
                    assignment=assign,
                    form=form,
                )


        description = ("Email {assign} scores ({tags})"
                       .format(assign=assign.display_name,
                               tags=', '.join([k.title() for k in form.kinds.data])))
        job = jobs.enqueue_job(
            scores_notify.email_scores,
            description=description,
            timeout=3600,
            course_id=cid,
            user_id=current_user.id,
            assignment_id=assign.id,
            subject=form.subject.data,
            reply_to=form.reply_to.data,
            body=form.body.data,
            dry_run=form.dry_run.data,
            score_tags=form.kinds.data)
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    else:
        form.kinds.data = assign.published_scores
        return render_template(
            'staff/jobs/notify_scores.html',
            courses=courses,
            current_course=current_course,
            assignment=assign,
            form=form,
        )


@admin.route("/course/<int:cid>/assignments/<int:aid>/scores.csv")
@is_staff(course_arg='cid')
def export_scores(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not Assignment.can(assign, current_user, 'export'):
        flash('Insufficient permissions', 'error')
        return abort(401)
    query = (Score.query.options(db.joinedload('backup'))
                  .filter_by(assignment=assign, archived=False))

    custom_items = ('time', 'is_late', 'email', 'group')
    items = custom_items + Enrollment.export_items + Score.export_items

    def generate_csv():
        """ Generate csv export of scores for assignment.
        Num Queries: ~2N queries for N scores.
        """
        # Yield Column Info as first row
        yield ','.join(items) + '\n'
        for score in query:
            csv_file = StringIO()
            csv_writer = csv.DictWriter(csv_file, fieldnames=items)
            submitters = score.backup.enrollment_info()
            group = [s.user.email for s in submitters]
            time_str = utils.local_time(score.backup.created, current_course)
            for submitter in submitters:
                data = {'email': submitter.user.email,
                        'time': time_str,
                        'is_late': score.backup.is_late,
                        'group': group}
                data.update(submitter.export)
                data.update(score.export)
                csv_writer.writerow(data)
            yield csv_file.getvalue()

    file_name = "{0}.csv".format(assign.name.replace('/', '-'))
    disposition = 'attachment; filename={0}'.format(file_name)

    return Response(stream_with_context(generate_csv()), mimetype='text/csv',
                    headers={'Content-Disposition': disposition})

@admin.route("/course/<int:cid>/assignments/<int:aid>/queues")
@is_staff(course_arg='cid')
def assignment_queues(cid, aid):
    courses, current_course = get_courses(cid)
    assignment = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not Assignment.can(assignment, current_user, 'grade'):
        flash('Insufficient permissions', 'error')
        return abort(401)

    queues = GradingTask.get_staff_tasks(assignment.id)

    incomplete = [q.grader.email for q in queues if q.completed != q.total]
    complete = [q.grader.email for q in queues if q.completed == q.total]

    mailto_link = "mailto://{0}?subject={1}&body={2}&cc={3}".format(
        current_user.email,
        "{0} grading queue is not finished".format(assignment.display_name),
        "Queue Link: {0}".format(url_for('admin.grading_tasks', _external=True)),
        ','.join(incomplete)
    )

    remaining = len(incomplete)
    percent_left = (1-(remaining/max(1, len(queues)))) * 100

    if current_user.email in incomplete:
        flash("Hmm... You aren't finished with your queue.", 'info')
    elif current_user.email in complete:
        flash("Nice! You are all done with your queue", 'success')
    else:
        flash("You don't have a queue for this assignment", 'info')

    return render_template('staff/grading/overview.html', courses=courses,
                           current_course=current_course,
                           assignment=assignment, queues=queues,
                           incomplete=incomplete, mailto=mailto_link,
                           remaining=remaining, percent_left=percent_left)

@admin.route("/course/<int:cid>/assignments/<int:aid>/queues/<int:uid>")
@is_staff(course_arg='cid')
def assignment_single_queue(cid, aid, uid):
    courses, current_course = get_courses(cid)
    assignment = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not Assignment.can(assignment, current_user, 'grade'):
        flash('Insufficient permissions', 'error')
        return abort(401)

    assigned_grader = User.get_by_id(uid)

    page = request.args.get('page', 1, type=int)
    tasks_query = GradingTask.query.filter_by(assignment=assignment,
                                              grader_id=uid)
    queue = (tasks_query.options(db.joinedload('assignment'))
                        .order_by(GradingTask.created.asc())
                        .paginate(page=page, per_page=20))

    remaining = tasks_query.filter_by(score_id=None).count()
    percent_left = (1-(remaining/max(1, queue.total))) * 100

    return render_template('staff/grading/queue.html', courses=courses,
                           current_course=current_course,
                           assignment=assignment, grader=assigned_grader,
                           queue=queue, remaining=remaining,
                           percent_left=percent_left)


@admin.route("/course/<int:cid>/assignments/<int:aid>/queues/new",
             methods=["GET", "POST"])
@is_staff(course_arg='cid')
def assign_grading(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    form = forms.CreateTaskForm()
    course_staff = sorted(current_course.get_staff(), key=lambda x: x.role)
    details = lambda e: "{0} - ({1})".format(e.user.email, e.role)
    form.staff.choices = [(utils.encode_id(e.user_id), details(e))
                          for e in course_staff]

    if not form.staff.data:
        # Select all by default
        form.staff.default = [u[0] for u in form.staff.choices]
        form.process()

    if form.validate_on_submit():
        # TODO: Use worker job for this (this is query intensive)
        selected_users = []
        for hash_id in form.staff.data:
            user = User.get_by_id(utils.decode_id(hash_id))
            if user and user.is_enrolled(cid, roles=STAFF_ROLES):
                selected_users.append(user)

        # Available backups
        data = assign.course_submissions()
        backups = set(b['backup']['id'] for b in data if b['backup'])
        students = set(b['user']['id'] for b in data if b['backup'])
        
        tasks = GradingTask.create_staff_tasks(backups, selected_users, aid, cid,
                                               form.kind.data)

        num_with_submissions = len(students)
        flash(("Created {0} tasks ({1} students) for {2} staff."
               .format(len(tasks), num_with_submissions, len(selected_users))),
              "success")
        return redirect(url_for('.assignment', cid=cid, aid=aid))

    # Return template with options for who has to grade.
    return render_template('staff/grading/assign_tasks.html',
                           current_course=current_course, assignment=assign,
                           form=form)

@admin.route("/course/<int:cid>/assignments/<int:aid>/autograde",
             methods=["POST"])
@is_staff(course_arg='cid')
def autograde(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)
    form = forms.CSRFForm()
    if form.validate_on_submit():
        job = jobs.enqueue_job(
            autograder.autograde_assignment,
            description='Autograde {}'.format(assign.display_name),
            result_kind='link',
            timeout=2 * 60 * 60,  # 2 hours
            course_id=cid,
            user_id=current_user.id,
            assignment_id=assign.id)
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    return redirect(url_for('.assignment', cid=cid, aid=aid))


@admin.route("/course/<int:cid>/assignments/<int:aid>/upload",
            methods=["GET","POST"])
@is_staff(course_arg='cid')
def upload(cid, aid):
    courses, current_course = get_courses(cid)
    upload_form = forms.BatchCSVScoreForm(kind='total')
    upload_form.submission_time.data = 'deadline'
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()

    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)
    if upload_form.validate_on_submit():
        job = jobs.enqueue_job(
            upload_scores.score_from_csv,
            description='Upload Scores for {}'.format(assign.display_name),
            result_kind='link',
            timeout=600,  # 5 mins
            course_id=cid,
            user_id=current_user.id,
            # params
            assign_id=assign.id,
            rows=upload_form.parsed,
            kind=upload_form.kind.data,
            message=upload_form.message.data,
            invalid=upload_form.invalid)
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))

    elif upload_form.error:
        flash(upload_form.error, 'error')
    return render_template('staff/course/assignment/assignment.upload.html',
                       upload_form=upload_form,
                       courses=courses,
                       current_course=current_course,
                       assignment=assign)


@admin.route("/course/<int:cid>/assignments/<int:aid>/effort",
             methods=["GET", "POST"])
@is_staff(course_arg='cid')
def effort_grading(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)
    form = forms.EffortGradingForm()
    if form.validate_on_submit():
        job = jobs.enqueue_job(
            effort.grade_on_effort,
            description='Effort Grading for {}'.format(assign.display_name),
            result_kind='link',
            timeout=1 * 60 * 60,  # 1 hour
            course_id=cid,
            user_id=current_user.id,
            assignment_id=assign.id,
            full_credit=float(form.full_credit.data),
            late_multiplier=float(form.late_multiplier.data),
            required_questions=int(form.required_questions.data),
            grading_url=url_for('admin.grading', bid='', _external=True))
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    else:
        return render_template(
            'staff/jobs/effort.html',
            courses=courses,
            current_course=current_course,
            assignment=assign,
            form=form,
        )

@admin.route("/course/<int:cid>/assignments/<int:aid>/moss",
             methods=["GET", "POST"])
@is_staff(course_arg='cid')
def start_moss_job(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    form = forms.MossSubmissionForm()
    if form.validate_on_submit():
        job = jobs.enqueue_job(
            moss.submit_to_moss,
            description='Moss Upload for {}'.format(assign.display_name),
            timeout=1800,
            course_id=cid,
            user_id=current_user.id,
            assignment_id=assign.id,
            moss_id=form.moss_userid.data,
            file_regex=form.file_regex.data or '.*',
            language=form.language.data,
            review_threshold=form.review_threshold.data or 101,
            num_results=form.num_results.data or 250)
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    else:
        return render_template(
            'staff/jobs/moss.html',
            courses=courses,
            current_course=current_course,
            assignment=assign,
            form=form,
        )

@admin.route("/course/<int:cid>/assignments/<int:aid>/moss-results",
             methods=["GET", "POST"])
@is_staff(course_arg='cid')
def assignment_moss_results(cid, aid):
    tag = request.args.get('tag')
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)
    moss_results = []
    last_run = MossResult.query.order_by(MossResult.run_time.desc()) \
        .join(MossResult.primary).filter_by(assignment_id = assign.id).first()
    print(last_run)
    if last_run:
        moss_results = MossResult.query.order_by(MossResult.similarity.desc()) \
            .filter_by(run_time = last_run.run_time).join(MossResult.primary) \
            .filter_by(assignment_id = assign.id).all()
    if tag:
        moss_results = [r for r in moss_results if tag in r.tags]
    return render_template('staff/plagiarism/list.assignment.html',
                           assignment=assign, moss_results=moss_results,
                           courses=courses, current_course=current_course)


@admin.route("/course/<int:cid>/assignments/<int:aid>/moss-results/<int:mid>",
             methods=["GET"])
@is_staff(course_arg='cid')
def get_moss_diffs(cid, aid, mid, diff_type='short'):

    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    form = forms.GradeForm()

    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    last_run = MossResult.query.order_by(MossResult.run_time.desc()) \
        .join(MossResult.primary).filter_by(assignment_id = assign.id).first()
    if last_run:
        moss_result = MossResult.query.order_by(MossResult.similarity.desc()) \
            .filter_by(run_time = last_run.run_time, id = mid) \
            .join(MossResult.primary).filter_by(assignment_id = assign.id).first()


    def get_diff_data(backup, matches):
        # get highlighted areas

        submitted_files = backup.files()
        tot_backups = Backup.query.filter(Backup.assignment_id == aid, Backup.submitter_id ==  backup.submitter_id).count()
        approved = {} # contains cleaned files, with no lines suspected of plagiarism
        for file in submitted_files:
            lines_lst = submitted_files[file].splitlines()
            all_lines = copy.deepcopy(lines_lst)
            file_matches = matches[file]
            for match in file_matches:
                for line in range(match[0], match[1] + 1):
                    all_lines[line - 1] = -1 # mark the offending lines for removal
            approved[file] = ''.join([line + '\n' for line in all_lines if line != -1])
            hlt = highlight.diff_files(submitted_files, approved, diff_type)

        # get the diff timelines
        user_ids = backup.owners()
        group = [User.query.get(uid).email for uid in user_ids]
        line_charts = []
        all_backups = (Backup.query.options(db.joinedload('messages'),
                                            db.joinedload('submitter'))
                             .filter(Backup.submitter_id.in_(set(user_ids)),
                                     Backup.assignment_id == assign.id)
                             .order_by(Backup.created.asc())).all()
        all_backups_dict = {}
        for this_backup in all_backups:
            if this_backup.submitter_id not in all_backups_dict:
                all_backups_dict[this_backup.submitter_id] = [this_backup]
            else:
                all_backups_dict[this_backup.submitter_id].append(this_backup)

        for user_id in user_ids:
            backups = []
            if user_id in all_backups_dict:
                backups = all_backups_dict[user_id]
            analyze.sort_by_client_time(backups)
            line_chart = analyze.generate_line_chart(backups, cid, User.query.get(user_id).email, aid)
            line_charts.append(line_chart)

        return {
            'backup': backup,
            'file_hlts': hlt,
            'total': tot_backups,
            'group': group,
            'graphs': line_charts
        }

    primary = get_diff_data(moss_result.primary, moss_result.primary_matches)
    secondary = get_diff_data(moss_result.secondary, moss_result.secondary_matches)

    def dict_slicer(dict, cols):
        cols = set(cols)
        return {k:v for k, v in dict.items() if k in cols}

    info = (
        ('Primary', dict_slicer(primary, 'backup total group'.split())),
        ('Secondary', dict_slicer(secondary, 'backup total group'.split())),
    )

    graphs = (
        ('Primary', dict_slicer(primary, 'group graphs'.split())),
        ('Secondary', dict_slicer(secondary, 'group graphs'.split())),
    )

    files = []
    # only include files common to both backups
    filenames = primary['file_hlts'].keys() & secondary['file_hlts'].keys()
    for filename in sorted(filenames):
        primary_data = (primary['backup'], filename, primary['file_hlts'][filename])
        secondary_data = (secondary['backup'], filename, secondary['file_hlts'][filename])
        files.append((primary_data, secondary_data))

    return render_template('staff/plagiarism/moss_diff.html',
                   assignment=assign, courses=courses, form=form,
                   info=info, graphs=graphs, files=files,
                   diff_type=diff_type, current_course=current_course, moss_result=moss_result)




@admin.route("/course/<int:cid>/assignments/<int:aid>/github",
             methods=["GET", "POST"])
@is_staff(course_arg='cid')
def start_github_search(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    form = forms.GithubSearchRecentForm()
    if form.validate_on_submit():
        job = jobs.enqueue_job(
            github_search.search_similar_repos,
            description='Github Search for {}'.format(assign.display_name),
            timeout=600,
            course_id=cid,
            user_id=current_user.id,
            assignment_id=assign.id,
            keyword=form.keyword.data,
            template_name=form.template_name.data,
            access_token=form.access_token.data,
            weeks_past=form.weeks_past.data,
            language=form.language.data,
            issue_title=form.issue_title.data,
            issue_body=form.issue_body.data)
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    else:
        return render_template(
            'staff/jobs/github_search.html',
            courses=courses,
            current_course=current_course,
            assignment=assign,
            form=form,
        )


@admin.route('/course/<int:cid>/assignments/<int:aid>/export/',
             methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def export_submissions(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        return abort(404)
    form = forms.ExportAssignment()
    if form.validate_on_submit():
        if form.anonymize.data:
            description = 'Anonymized Export'
        else:
            description = 'Final Submission Export'

        job = jobs.enqueue_job(
            export.export_assignment,
            description='{} for {}'.format(description, assign.display_name),
            timeout=3600,
            user_id=current_user.id,
            course_id=cid,
            assignment_id=aid,
            anonymized=form.anonymize.data,
            result_kind='link')
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    else:
        return render_template(
            'staff/jobs/export.html',
            courses=courses,
            assignment=assign,
            current_course=current_course,
            form=form,
        )

@admin.route("/course/<int:cid>/assignments/<int:aid>/checkpoint",
             methods=["GET", "POST"])
@is_staff(course_arg='cid')
def checkpoint_grading(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    form = forms.CheckpointCreditForm()
    if form.validate_on_submit():
        timeout = 3600 if form.grade_backups.data else 600
        job = jobs.enqueue_job(
            checkpoint.assign_scores,
            description='Checkpoint Scoring for {}'.format(assign.display_name),
            timeout=timeout,
            result_kind='link',
            course_id=cid,
            user_id=current_user.id,
            assign_id=assign.id,
            score=form.score.data,
            kind=form.kind.data,
            message=form.message.data,
            deadline=form.deadline.data,
            include_backups=form.include_backups.data,
            grade_backups=form.grade_backups.data)
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    else:
        if not form.kind.data:
            form.kind.default = 'checkpoint 1'
        if not form.deadline.data:
            form.deadline.default = utils.local_time_obj(assign.due_date, assign.course)
        form.process()

        return render_template(
            'staff/jobs/checkpoint.html',
            courses=courses,
            current_course=current_course,
            assignment=assign,
            form=form,
        )


##############
# Enrollment #
##############

@admin.route("/course/<int:cid>/enrollment", methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def enrollment(cid):
    courses, current_course = get_courses(cid)
    form = forms.EnrollmentForm()
    export_form = forms.EnrollmentExportForm()
    if form.validate_on_submit():
        email, role = form.email.data, form.role.data
        Enrollment.enroll_from_form(cid, form)
        flash("Added {email} as {role}".format(
            email=email, role=role), "success")

    students = current_course.get_students()
    staff = current_course.get_staff()
    lab_assistants = current_course.get_participants([LAB_ASSISTANT_ROLE])

    return render_template('staff/course/enrollment/enrollment.html',
                           enrollments=students, staff=staff,
                           lab_assistants=lab_assistants,
                           form=form,
                           export_form=export_form,
                           unenroll_form=forms.CSRFForm(),
                           courses=courses,
                           current_course=current_course)

@admin.route("/course/<int:cid>/<int:user_id>/unenroll", methods=['POST'])
@is_staff(course_arg='cid')
def unenrollment(cid, user_id):
    user = User.query.filter_by(id=user_id).one_or_none()
    if user:
        enrollment = user.is_enrolled(cid)
        if enrollment:
            enrollment.unenroll()
            flash("{email} has been unenrolled".format(email=user.email), "success")
        else:
            flash("{email} is not enrolled".format(email=user.email), "warning")
    else:
        flash("Unknown user", "warning")

    return redirect(url_for(".enrollment", cid=cid))

@admin.route("/course/<int:cid>/enrollment/batch",
             methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def batch_enroll(cid):
    courses, current_course = get_courses(cid)
    batch_form = forms.BatchEnrollmentForm()
    if batch_form.validate_on_submit():
        new, updated = Enrollment.enroll_from_csv(cid, batch_form)
        msg = ("Added {new}, updated {old} {role} enrollments"
               .format(new=new, role=batch_form.role.data, old=updated))
        flash(msg, "success")
        return redirect(url_for(".enrollment", cid=cid))

    return render_template('staff/course/enrollment/enrollment.batch.html',
                           batch_form=batch_form,
                           courses=courses,
                           current_course=current_course)

@admin.route("/course/<int:cid>/enrollment/csv", methods=['POST'])
@is_staff(course_arg='cid')
def enrollment_csv(cid):
    export_form = forms.EnrollmentExportForm()
    courses, current_course = get_courses(cid)
    if export_form.validate_on_submit():
        roles = export_form.roles.data
        query = (Enrollment.query.options(db.joinedload('user'))
                       .filter_by(course_id=cid)
                       .filter(Enrollment.role.in_(roles))
                       .order_by(Enrollment.role))

        file_name = "{0}-roster.csv".format(current_course.offering.replace('/', '-'))
        disposition = 'attachment; filename={0}'.format(file_name)
        items = User.export_items + Enrollment.export_items

        def row_to_csv(row):
            return [row.export, row.user.export]

        csv_generator = utils.generate_csv(query, items, row_to_csv)

        return Response(stream_with_context(csv_generator),
                        mimetype='text/csv',
                        headers={'Content-Disposition': disposition})
    flash('Invalid roles to export.', 'error')
    return redirect(url_for(".enrollment", cid=cid))

@admin.route("/clients/", methods=['GET', 'POST'])
@is_staff()
def clients():
    courses, current_course = get_courses()
    clients = Client.query.order_by(Client.active).all()
    my_clients = [client for client in clients if client.user_id == current_user.id]
    form = forms.ClientForm(client_secret=utils.generate_secret_key())
    if form.validate_on_submit():
        client = Client(
                user=current_user,
                active=True if current_user.is_admin else False)
        form.populate_obj(client)
        db.session.add(client)
        db.session.commit()

        flash('OAuth client "{}" added'.format(client.name), "success")
        return redirect(url_for(".clients"))

    return render_template('staff/clients.html',
            clients=clients,
            my_clients=my_clients,
            form=form,
            courses=courses)

@admin.route("/clients/<string:client_id>", methods=['GET', 'POST'])
@is_oauth_client_owner('client_id')
def client(client_id):
    courses, current_course = get_courses()

    client = Client.query.get(client_id)
    # Show the client owner's email in edit form when owner exists
    client.owner = client.user.email if client.user else ""
    form = forms.EditClientForm(obj=client)
    # Hide the active field and scopes if not an admin
    if not current_user.is_admin:
        del form.active
        del form.default_scopes
    if form.validate_on_submit():
        # Be careful not to overwrite user data
        if not form.user_id.data or not form.user.data:
            del form.user_id, form.user
        form.populate_obj(client)
        if form.roll_secret.data:
            client.client_secret = utils.generate_secret_key()
            flash_msg = ('OAuth client "{}" updated with new secret: "{}"'
                         .format(client.name, client.client_secret))
        else:
            flash_msg = ('OAuth client "{}" updated without changing the secret'
                         .format(client.name))
        db.session.commit()
        flash(flash_msg, "success")
        return redirect(url_for(".clients"))
    return render_template('staff/edit_client.html', client=client, form=form, courses=courses)

################
# Student View #
################

@admin.route("/course/<int:cid>/<string:email>", methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def student_view(cid, email):

    form = forms.EnrollmentForm()
    if form.validate_on_submit():
        if form.email.data != email:
            flash("You cannot change the user's email.", 'error')
        else:
            email, role = form.email.data, form.role.data
            Enrollment.enroll_from_form(cid, form)
            flash('Edited User Successfully', 'success')
    else:
        if form.is_submitted():
            flash('There is an issue with your request.', 'error')

    courses, current_course = get_courses(cid)
    assignments = current_course.assignments

    student = User.lookup(email)
    if not student:
        abort(404)

    enrollment = student.is_enrolled(cid)
    if not enrollment:
        flash("This email is not enrolled", 'warning')

    assignments = {
        'active': [a.user_status(student, staff_view=True) for a in assignments
                   if a.active],
        'inactive': [a.user_status(student, staff_view=True) for a in assignments
                     if not a.active]
    }

    moss_results = MossResult.query.order_by(MossResult.run_time) \
        .group_by(MossResult.primary_id, MossResult.secondary_id) \
        .order_by(MossResult.similarity.desc()) \
        .join(MossResult.primary).join(Backup.submitter).filter_by(id=student.id).all()

    return render_template('staff/student/overview.html',
                           courses=courses, current_course=current_course,
                           student=student, enrollment=enrollment,
                           assignments=assignments, moss_results=moss_results, form=form)

@admin.route("/course/<int:cid>/<string:email>/<int:aid>/timeline")
@is_staff(course_arg='cid')
def assignment_timeline(cid, email, aid):
    courses, current_course = get_courses(cid)

    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    student = User.lookup(email)
    if not student.is_enrolled(cid):
        flash("This user is not enrolled", 'warning')

    stats = assign.user_timeline(student.id)

    return render_template('staff/student/assignment.timeline.html',
                           courses=courses, current_course=current_course,
                           student=student, assignment=assign,
                           submitters=stats['submitters'],
                           timeline=stats['timeline'])


@admin.route("/course/<int:cid>/<string:email>/<int:aid>")
@is_staff(course_arg='cid')
def student_assignment_detail(cid, email, aid):
    courses, current_course = get_courses(cid)
    page = request.args.get('page', 1, type=int)

    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    student = User.lookup(email)
    if not student:
        abort(404)
    if not student.is_enrolled(cid):
        flash("This user is not enrolled", 'warning')

    assignment_stats = assign.user_status(student, staff_view=True)

    user_ids = assign.active_user_ids(student.id)

    latest = assignment_stats.final_subm or assign.backups(user_ids).first()

    stats = {
        'num_backups': assign.backups(user_ids).count(),
        'num_submissions': assign.submissions(user_ids).count(),
        'current_q': None,
        'attempts': None,
        'latest': latest,
        'analytics': latest and latest.analytics()
    }

    backups = (Backup.query.options(db.joinedload('scores'),
                                    db.joinedload('submitter'))
                     .filter(Backup.submitter_id.in_(user_ids),
                             Backup.assignment_id == assign.id)
                     .order_by(Backup.flagged.desc(), Backup.submit.desc(),
                               Backup.created.desc()))

    paginate = backups.paginate(page=page, per_page=15)

    if stats['analytics']:
        stats['current_q'] = stats['analytics'].get('question')
        stats['attempts'] = (stats['analytics'].get('history', {})
                                               .get('all_attempts'))

    return render_template('staff/student/assignment.html',
                           courses=courses, current_course=current_course,
                           student=student, assignment=assign,
                           add_member_form=forms.StaffAddGroupFrom(),
                           paginate=paginate,
                           csrf_form=forms.CSRFForm(),
                           stats=stats,
                           assign_status=assignment_stats)

@admin.route("/course/<int:cid>/<string:email>/<int:aid>/<hashid:backup_id>")
@is_staff(course_arg='cid')
def student_backups_overview(cid, email, aid, backup_id):
    courses, current_course = get_courses(cid)

    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    student = User.lookup(email)
    if not student.is_enrolled(cid):
        flash("This user is not enrolled", 'warning')

    user_id = {student.id}
    timeline_stats = assign.user_timeline(student.id, backup_id)
    partner_ids = assign.active_user_ids(student.id) - user_id

    # get students.id's backups
    backups = (Backup.query.options(db.joinedload('messages'),
                                    db.joinedload('submitter'))
                     .filter(Backup.submitter_id.in_(user_id),
                             Backup.assignment_id == assign.id)
                     .order_by(Backup.created.asc())).all()
    analyze.sort_by_client_time(backups)

    # get partners' backups
    partner_backups = (Backup.query.options(db.joinedload('messages'),
                                    db.joinedload('submitter'))
                     .filter(Backup.submitter_id.in_(partner_ids),
                             Backup.assignment_id == assign.id)
                     .order_by(Backup.created.asc())).all()
    analyze.sort_by_client_time(partner_backups)

    diff_dict = analyze.get_diffs(backups, backup_id, partner_backups)
    if not diff_dict:
        # either no unique backups or wrong backup_id
        return abort(404)

    group = [User.query.get(o) for o in backups[0].owners()] #Todo (Stan): fix?

    stats_list = diff_dict["stats"]
    files_list = diff_dict["files"]
    partner_files_list = diff_dict["partners"]
    backup_id = diff_dict["backup_id"] # relevant backup_id might be different
    prev_backup_id = diff_dict["prev_backup_id"]
    next_backup_id = diff_dict["next_backup_id"]

    # calculate starting diff for template

    start_index = [i for i, stat in enumerate(stats_list) if stat["bid"] == backup_id]
    if start_index: # edge case for 1st backup; no diff will be found
        start_index = start_index[0]
    else:
        start_index = 0
    return render_template('staff/student/assignment.overview.html',
                           current_course=current_course,
                           student=student, assignment=assign,
                           stats_list=stats_list, files_list=files_list,
                           partner_files_list=partner_files_list,
                           group=group, start_index=start_index,
                           prev_backup_id = prev_backup_id,
                           next_backup_id = next_backup_id,
                           submitters=timeline_stats['submitters'],
                           timeline=timeline_stats['timeline'])

@admin.route("/course/<int:cid>/<string:email>/<int:aid>/graph")
@is_staff(course_arg='cid')
def student_assignment_graph_detail(cid, email, aid):
    courses, current_course = get_courses(cid)

    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    student = User.lookup(email)
    if not student.is_enrolled(cid):
        flash("This user is not enrolled", 'warning')

    user_ids = list(assign.active_user_ids(student.id))
    user_ids.remove(student.id) # should always exist
    user_ids.insert(0, student.id) # insert to front of list

    line_charts = []

    all_backups = (Backup.query.options(db.joinedload('messages'),
                                        db.joinedload('submitter'))
                         .filter(Backup.submitter_id.in_(set(user_ids)),
                                 Backup.assignment_id == assign.id)
                         .order_by(Backup.created.asc())).all()
    all_backups_dict = {}

    for backup in all_backups:
        if backup.submitter_id not in all_backups_dict:
            all_backups_dict[backup.submitter_id] = [backup]
        else:
            all_backups_dict[backup.submitter_id].append(backup)

    for user_id in user_ids:
        backups = []
        if user_id in all_backups_dict:
            backups = all_backups_dict[user_id]
        analyze.sort_by_client_time(backups)
        line_chart = analyze.generate_line_chart(backups, cid, User.query.get(user_id).email, aid)
        line_charts.append(line_chart)

    group = [User.query.get(owner) for owner in user_ids] #TODO

    return render_template('staff/student/assignment.graph.html',
                           current_course=current_course,
                           student=student, assignment=assign,
                           group=group,
                           graphs=line_charts)
##############
# Extensions #
##############
@admin.route("/course/<int:cid>/extensions")
@is_staff(course_arg='cid')
def list_extensions(cid):
    courses, current_course = get_courses(cid)

    extensions = (Extension.query.join(Extension.assignment)
                           .options(db.joinedload('user'),
                                    db.joinedload('staff'),
                                    db.joinedload('assignment'))
                           .filter(Assignment.course_id == cid).all())
    csrf_form = forms.CSRFForm()
    return render_template('staff/course/extension/extensions.html',
                            courses=courses, current_course=current_course,
                            extensions=extensions, csrf_form=csrf_form)

@admin.route("/course/<int:cid>/extensions/new",
                methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def create_extension(cid):
    courses, current_course = get_courses(cid)

    form = forms.ExtensionForm()
    form.assignment_id.choices = sorted(
        ((a.id, a.display_name) for a in current_course.assignments),
        key=lambda a: a[1],
    )

    if request.method == "GET":
        # Prefill fields if not set
        form.submission_time.default = 'deadline'
        if not form.assignment_id.data:
            form.assignment_id.default = request.args.get('aid')
        form.process() # Update defaults & choices
        if not form.email.data:
            form.email.data = request.args.get('email')
        if not form.expires.data:
            extra_week =  utils.local_time_obj(dt.datetime.utcnow(), current_course) + dt.timedelta(days=7)
            form.expires.data = extra_week.replace(hour=23, minute=59, second=59)

    if form.validate_on_submit():
        assign = Assignment.query.filter_by(id=form.assignment_id.data).one_or_none()
        student = User.lookup(form.email.data)
        if Extension.get_extension(student, assign):
            flash("{} already has an extension".format(form.email.data), 'danger')
        else:
            group_members = assign.active_user_ids(student.id)
            ext = Extension.query.filter(Extension.assignment == assign, Extension.user_id.in_(group_members)).first()
            if ext:
                Extension.delete(ext)
            expires = utils.server_time_obj(form.expires.data, current_course)
            custom_time = form.get_submission_time(assign)
            ext = Extension.create(staff=current_user, assignment=assign, user=student,
                            message=form.reason.data, expires=expires,
                            custom_submission_time=custom_time)
            emails = ', '.join([u.email for u in ext.members()])
            flash("Granted a extension on {} for {} ".format(assign.display_name,
                                                             emails), 'success')
            return redirect(url_for('.list_extensions', cid=cid))

    return render_template('staff/course/extension/extension.new.html',
                           form=form, courses=courses,
                           current_course=current_course)

@admin.route("/course/<int:cid>/extensions/<hashid:ext_id>", methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def edit_extension(cid, ext_id):
    courses, current_course = get_courses(cid)
    extension = Extension.query.get_or_404(ext_id)
    if not Extension.can(extension, current_user, 'edit'):
        abort(401)

    # Add our expected form element values
    extension.email = extension.user.email
    extension.reason = extension.message
    extension.expires = utils.local_time_obj(extension.expires, current_course)
    extension.submission_time = 'other'
    # Don't show submission helper
    form = forms.ExtensionForm(obj=extension)
    form.assignment_id.choices = sorted(
        ((a.id, a.display_name) for a in current_course.assignments),
        key=lambda a: a[1],
    )

    if form.validate_on_submit():
        assign = Assignment.query.filter_by(id=form.assignment_id.data).one_or_none()
        student = User.lookup(form.email.data)
        # If changing user ensure that they don't already have an extension
        if form.email.data != extension.user.email and Extension.get_extension(student, assign):
            flash("{} already has an extension".format(form.email.data), 'danger')
        else:
            group_members = assign.active_user_ids(student.id)
            ext = Extension.query.filter(Extension.assignment == assign, Extension.user_id.in_(group_members - {student.id})).first()
            if ext:
                Extension.delete(ext)
            expires = utils.server_time_obj(form.expires.data, current_course)
            custom_time = form.get_submission_time(assign)
            extension.staff = current_user
            extension.assignment = assign
            extension.user = student
            extension.message = form.reason.data
            extension.expires = expires
            extension.custom_submission_time = custom_time
            db.session.add(extension)
            db.session.commit()
            emails = ', '.join([u.email for u in extension.members()])
            flash("Updated an extension on {} for {} ".format(assign.display_name,
                                                             emails), 'success')
            return redirect(url_for('.list_extensions', cid=cid))

    return render_template('staff/course/extension/extension.edit.html',
                           form=form, courses=courses,
                           current_course=current_course,
                           extension=extension)


@admin.route("/course/<int:cid>/extensions/<hashid:ext_id>/delete", methods=['POST'])
@is_staff(course_arg='cid')
def delete_extension(cid, ext_id):
    extension = Extension.query.get_or_404(ext_id)
    if not Extension.can(extension, current_user, 'delete'):
        abort(401)

    if forms.CSRFForm().validate_on_submit():
        Extension.delete(extension)
        flash("Revoked extension", "success")
        return redirect(url_for('.list_extensions', cid=cid))
    abort(401)


########################
# Student view actions #
########################

@admin.route("/course/<int:cid>/<string:email>/<int:aid>/add_member",
             methods=["POST"])
@is_staff(course_arg='cid')
def staff_group_add(cid, email, aid):
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        flash('Cannot access assignment', 'error')
        return abort(404)

    form = forms.StaffAddGroupFrom()
    result_page = url_for('.student_assignment_detail', cid=cid,
                          email=email, aid=aid)

    student = User.lookup(email)
    if not student:
        return abort(404)

    if form.validate_on_submit():
        target = User.lookup(form.email.data)
        if not target or not target.is_enrolled(cid):
            flash("This user is not enrolled", 'warning')
            return redirect(result_page)
        try:
            Group.force_add(current_user, student, target, assign)
        except BadRequest as e:
            flash("Error: {}".format(str(e.description)), 'error')
            return redirect(result_page)

    return redirect(result_page)

@admin.route("/course/<int:cid>/<string:email>/<int:aid>/remove_member",
             methods=["POST"])
@is_staff(course_arg='cid')
def staff_group_remove(cid, email, aid):
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        return abort(404)

    student = User.lookup(email)
    if not student:
        abort(404)

    result_page = url_for('.student_assignment_detail', cid=cid,
                          email=email, aid=aid)

    form = forms.CSRFForm()
    if form.validate_on_submit():
        target = User.lookup(request.form['target'])
        if not target:
            flash('{} does not exist'.format(request.form['target']), 'error')
            return redirect(result_page)
        try:
            Group.force_remove(current_user, student, target, assign)
        except BadRequest as e:
            flash("Error: {}".format(str(e.description)), 'error')
    return redirect(result_page)

@admin.route("/course/<int:cid>/<string:email>/<int:aid>/flag",
             methods=["POST"])
@is_staff(course_arg='cid')
def staff_flag_backup(cid, email, aid):
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        return abort(404)
    result_page = url_for('.student_assignment_detail', cid=cid,
                          email=email, aid=aid)

    student = User.lookup(email)
    if not student:
        abort(404)
    user_ids = assign.active_user_ids(student.id)

    bid = request.form.get('bid')

    form = forms.CSRFForm()
    if form.validate_on_submit():
        backup = Backup.query.filter_by(id=utils.decode_id(bid),
                                        assignment=assign).one_or_none()
        if not backup:
            flash('{} does not exist'.format(bid, 'error'))
            return redirect(result_page)

        if not backup.flagged:
            result = assign.flag(backup.id, user_ids)
            flash('Flagged backup {} for grading'.format(bid), 'success')
        else:
            result = assign.unflag(backup.id, user_ids)
            flash('Removed grading flag on {}'.format(bid), 'success')

    return redirect(result_page)


@admin.route("/course/<int:cid>/<string:email>/<int:aid>/submit",
             methods=["GET", "POST"])
@is_staff(course_arg='cid')
def staff_submit_backup(cid, email, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one_or_none()
    if not assign or not Assignment.can(assign, current_user, 'grade'):
        return abort(404)
    student = User.lookup(email)
    if not student:
        abort(404)
    user_ids = assign.active_user_ids(student.id)
    # TODO: DRY - Unify with student upload code - should just be a function
    form = forms.StaffUploadSubmissionForm()
    if form.validate_on_submit():
        backup = Backup.create(
            submitter=student,
            creator=current_user,
            assignment=assign,
            submit=True,
            custom_submission_time=form.get_submission_time(assign),
        )
        if form.upload_files.upload_backup_files(backup):
            db.session.add(backup)
            db.session.commit()
            if assign.autograding_key and assign.continuous_autograding:
                try:
                    autograder.submit_continuous(backup)
                except ValueError as e:
                    flash('Did not send to autograder: {}'.format(e), 'warning')
            flash('Uploaded submission'.format(backup.hashid), 'success')
            return redirect(url_for('.grading', bid=backup.id))
    return render_template(
        'staff/student/submit.html',
        current_course=current_course,
        courses=courses,
        student=student,
        assignment=assign,
        upload_form=form,
    )


########
# Jobs #
########

@admin.route('/course/<int:cid>/jobs/')
@is_staff(course_arg='cid')
def course_jobs(cid):
    courses, current_course = get_courses(cid)
    jobs = Job.query.filter_by(course_id=cid).all()
    return render_template(
        'staff/jobs/index.html',
        courses=courses,
        current_course=current_course,
        jobs=jobs,
    )

@admin.route('/course/<int:cid>/jobs/<int:job_id>/')
@is_staff(course_arg='cid')
def course_job(cid, job_id):
    courses, current_course = get_courses(cid)
    job = Job.query.get_or_404(job_id)
    if job.course_id != cid:
        abort(404)
    return render_template(
        'staff/jobs/job.html',
        courses=courses,
        current_course=current_course,
        job=job,
    )

@admin.route('/course/<int:cid>/jobs/test/', methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def start_test_job(cid):
    courses, current_course = get_courses(cid)
    form = forms.TestJobForm()
    if form.validate_on_submit():
        job = jobs.enqueue_job(
            example.test_job,
            description='Test Job',
            course_id=cid,
            duration=form.duration.data,
            make_file=form.make_file.data,
            should_fail=form.should_fail.data,
            result_kind='html')
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    else:
        return render_template(
            'staff/jobs/test.html',
            courses=courses,
            current_course=current_course,
            form=form,
        )

##########
# Canvas #
##########

def get_external_names(canvas_course):
    try:
        return {
            a['id']: a['name'] for a in canvas_api.get_assignments(canvas_course)
        }
    except requests.exceptions.HTTPError as e:
        flash("Could not retrieve bCourses assignments ({})".format(e.response.status_code), "danger")
        return {}

@admin.route('/course/<int:cid>/canvas/')
@is_staff(course_arg='cid')
def canvas_course(cid):
    courses, current_course = get_courses(cid)
    canvas_course = CanvasCourse.by_course_id(cid)
    if not canvas_course:
        return redirect(url_for('.edit_canvas_course', cid=cid))
    canvas_assignments = sorted(
        canvas_course.canvas_assignments,
        key=lambda ca: ca.assignment.display_name,
    )
    external_names = get_external_names(canvas_course)
    return render_template(
        'staff/canvas/index.html',
        courses=courses,
        current_course=current_course,
        canvas_course=canvas_course,
        canvas_assignments=canvas_assignments,
        external_names=external_names,
    )

@admin.route('/course/<int:cid>/canvas/edit/', methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def edit_canvas_course(cid):
    courses, current_course = get_courses(cid)
    canvas_course = CanvasCourse.by_course_id(cid)
    form = forms.CanvasCourseForm()
    if not canvas_course:
        canvas_course = CanvasCourse(course_id=cid)
    else:
        form.url.data = canvas_course.url
    if form.validate_on_submit():
        form.populate_canvas_course(canvas_course)
        db.session.add(canvas_course)
        db.session.commit()
        flash("Saved bCourses configuration", "success")
        return redirect(url_for('.canvas_course', cid=cid))
    return render_template(
        'staff/canvas/edit.html',
        courses=courses,
        current_course=current_course,
        form=form,
    )

@admin.route('/course/<int:cid>/canvas/delete/', methods=['POST'])
@is_staff(course_arg='cid')
def delete_canvas_course(cid):
    if forms.CSRFForm().validate_on_submit():
        canvas_course = CanvasCourse.by_course_id(cid)
        db.session.delete(canvas_course)
        db.session.commit()
        flash("Deleted bCourses configuration", "success")
        return redirect(url_for('.course', cid=cid))
    abort(401)

@admin.route('/course/<int:cid>/canvas/assignments/new/',
    defaults={'canvas_assignment_id': None}, methods=['GET', 'POST'])
@admin.route('/course/<int:cid>/canvas/assignments/<int:canvas_assignment_id>/edit/',
    methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def edit_canvas_assignment(cid, canvas_assignment_id):
    courses, current_course = get_courses(cid)
    canvas_course = CanvasCourse.by_course_id(cid)
    if not canvas_course:
        abort(404)
    if canvas_assignment_id:
        canvas_assignment = CanvasAssignment.query.get_or_404(canvas_assignment_id)
        form = forms.CanvasAssignmentForm(obj=canvas_assignment)
    else:
        canvas_assignment = CanvasAssignment(canvas_course_id=canvas_course.id)
        form = forms.CanvasAssignmentForm()
    form.external_id.choices = sorted(
        get_external_names(canvas_course).items(),
        key=lambda p: p[1],
    )
    form.assignment_id.choices = sorted(
        ((a.id, a.display_name) for a in current_course.assignments),
        key=lambda p: p[1],
    )
    if form.validate_on_submit():
        form.populate_obj(canvas_assignment)
        db.session.add(canvas_assignment)
        db.session.commit()
        flash("Saved assignment", "success")
        return redirect(url_for('.canvas_course', cid=cid))
    return render_template(
        'staff/canvas/assignment.html',
        courses=courses,
        current_course=current_course,
        form=form,
    )

@admin.route('/course/<int:cid>/canvas/assignments/<int:canvas_assignment_id>/delete/',
    methods=['POST'])
@is_staff(course_arg='cid')
def delete_canvas_assignment(cid, canvas_assignment_id):
    courses, current_course = get_courses(cid)
    canvas_assignment = CanvasAssignment.query.get_or_404(canvas_assignment_id)
    if forms.CSRFForm().validate_on_submit():
        db.session.delete(canvas_assignment)
        db.session.commit()
        flash("Removed assignment", "success")
        return redirect(url_for('.canvas_course', cid=cid))
    abort(401)

def enqueue_canvas_upload_job(canvas_assignment):
    return jobs.enqueue_job(
        server.canvas.jobs.upload_scores,
        description='bCourses Upload for {}'.format(
            canvas_assignment.assignment.display_name),
        course_id=canvas_assignment.canvas_course.course_id,
        user_id=current_user.id,
        canvas_assignment_id=canvas_assignment.id)

@admin.route('/course/<int:cid>/canvas/assignments/<int:canvas_assignment_id>/upload/',
    methods=['POST'])
@is_staff(course_arg='cid')
def upload_canvas_assignment(cid, canvas_assignment_id):
    canvas_assignment = CanvasAssignment.query.get_or_404(canvas_assignment_id)
    if forms.CSRFForm().validate_on_submit():
        job = enqueue_canvas_upload_job(canvas_assignment)
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    abort(401)

@admin.route('/course/<int:cid>/canvas/upload/', methods=['POST'])
@is_staff(course_arg='cid')
def upload_canvas_course(cid):
    canvas_course = CanvasCourse.by_course_id(cid)
    if not canvas_course:
        abort(404)
    if forms.CSRFForm().validate_on_submit():
        for canvas_assignment in canvas_course.canvas_assignments:
            enqueue_canvas_upload_job(canvas_assignment)
        return redirect(url_for('.course_jobs', cid=cid))
    abort(401)

@admin.route('/course/<int:cid>/canvas/enroll/', methods=['POST'])
@is_staff(course_arg='cid')
def enroll_canvas_course(cid):
    canvas_course = CanvasCourse.by_course_id(cid)
    if not canvas_course:
        abort(404)
    if forms.CSRFForm().validate_on_submit():
        job = jobs.enqueue_job(
            server.canvas.jobs.enroll_students,
            description='Enroll students from bCourses',
            course_id=cid,
            user_id=current_user.id,
            canvas_course_id=canvas_course.id)
        return redirect(url_for('.course_job', cid=cid, job_id=job.id))
    abort(401)
