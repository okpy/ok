import collections
import csv
from functools import wraps
from io import StringIO

from flask import (Blueprint, render_template, flash, redirect, Response,
                   url_for, abort, request, stream_with_context)

from flask_login import current_user
import pytz

from server.models import (User, Course, Assignment, Enrollment, Version,
                           GradingTask, Backup, Score, db)
from server.constants import STAFF_ROLES, STUDENT_ROLE
from server.extensions import cache
import server.forms as forms
import server.highlight as highlight


admin = Blueprint('admin', __name__)


def convert_to_pacific(date):
    # TODO Move to UTILS
    return date.replace(tzinfo=pytz.utc)

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
            flash("You are not on the course staff", "error")
            return redirect(url_for("student.index"))
        return wrapper
    return decorator


def get_courses(cid=None):
    #  TODO : The decorator could add these to the routes
    if current_user.is_authenticated and current_user.is_admin:
        courses = Course.query.all()
    else:
        enrollments = current_user.enrollments(roles=STAFF_ROLES)
        courses = [e.course for e in enrollments]
    if not cid:
        return courses, []

    matching_courses = [c for c in courses if c.id == cid]
    if len(matching_courses) == 0:
        abort(401)  # TODO to actual error page
    current_course = matching_courses[0]
    return courses, current_course


@admin.route("/")
@is_staff()
def index():
    courses, current_course = get_courses()
    if courses:
        return redirect(url_for(".course_assignments", cid=courses[0].id))
    return render_template('staff/index.html', courses=courses)

@admin.route('/grading')
@is_staff()
def grading_tasks(username=None):
    courses, current_course = get_courses()
    page = request.args.get('page', 1, type=int)
    queue = (GradingTask.query
                        .filter_by(grader=current_user)
                        .options(db.joinedload('assignment'))
                        .order_by(GradingTask.score_id.desc())
                        .order_by(GradingTask.created.desc())
                        .paginate(page=page, per_page=20))
    remaining = (GradingTask.query
                            .filter_by(grader=current_user, score_id=None)
                            .count())
    percent_left = (1-(remaining/max(1, queue.total))) * 100
    return render_template('staff/grading/queue.html', courses=courses,
                           queue=queue, remaining=remaining,
                           percent_left=percent_left)

def grading_view(backup, form=None):
    """ General purpose grading view. Used by routes."""
    courses, current_course = get_courses()
    assign = backup.assignment
    diff_type = request.args.get('diff', None)
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
    for filename, lines in files.items():
        for line in lines:
            line.comments = comments[(filename, line.line_after)]

    group = [User.query.get(o) for o in backup.owners()]
    scores = [s for s in backup.scores if not s.archived]
    task = backup.grading_tasks
    if task:
        # Choose the first grading_task
        task = task[0]

    return render_template(
        'staff/grading/code.html', courses=courses, assignment=assign,
        backup=backup, group=group, scores=scores, files=files,
        diff_type=diff_type, task=task, form=form
    )

@admin.route('/grading/<hashid:bid>')
@is_staff()
def grading(bid):
    backup = Backup.query.get(bid)
    if not (backup and Backup.can(backup, current_user, "grade")):
        abort(404)
    form = forms.GradeForm()
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
    return grading_view(backup, form=form)

@admin.route('/grading/<hashid:bid>/grade', methods=['POST'])
@is_staff()
def grade(bid):
    """ Used as a form submission endpoint. """
    backup = Backup.query.get(bid)
    if not backup:
        abort(404)
    if not Backup.can(backup, current_user, 'grade'):
        flash("You do not have permission to score this assignment.", "warning")
        abort(401)

    form = forms.GradeForm()
    score_kind = form.kind.data.strip().lower()
    if score_kind == "composition":
        form = forms.CompositionScoreForm()

    if not form.validate_on_submit():
        return grading_view(backup, form=form)

    # Archive old scores with the same kind
    existing = Score.query.filter_by(backup=backup, kind=score_kind).first()
    if existing:
        existing.public = False
        existing.archived = True

    model = Score(backup=backup, grader=current_user,
                  assignment_id=backup.assignment_id)
    form.populate_obj(model)
    db.session.add(model)
    db.session.commit()

    cache.delete_memoized(User.num_grading_tasks, repr(current_user))

    if request.args.get('queue'):
        # TODO: Find next submission in queue and redirect to that.
        pass
    flash("Added {} score.".format(model.kind), "success")
    route = ".composition" if score_kind == "composition" else ".grading"
    return redirect(url_for(route, bid=backup.id))


@admin.route("/client/<name>", methods=['GET', 'POST'])
@is_staff()
def client_version(name):
    version = Version.query.filter_by(name=name).one_or_none()
    if not version:
        version = Version(name=name)
    form = forms.VersionForm(obj=version)
    if form.validate_on_submit():
        form.populate_obj(version)

        db.session.add(version)
        db.session.commit()

        flash(name + " version updated successfully.", "success")
        return redirect(url_for(".client_version", name=name))

    return render_template('staff/client_version.html',
                           version=version, form=form)


@admin.route("/course/<int:cid>")
@is_staff(course_arg='cid')
def course(cid):
    return redirect(url_for(".course_assignments", cid=cid))
    # courses, current_course = get_courses(cid)
    # return render_template('staff/course/index.html',
    #                       courses=courses, current_course=current_course)


@admin.route("/course/<int:cid>/assignments")
@is_staff(course_arg='cid')
def course_assignments(cid):
    courses, current_course = get_courses(cid)
    assgns = current_course.assignments
    active_asgns = [a for a in assgns if a.active]
    due_asgns = [a for a in assgns if not a.active]
    # TODO CLEANUP : Better way to send this data to the template.

    return render_template('staff/course/assignments.html',
                           courses=courses, current_course=current_course,
                           active_asgns=active_asgns, due_assgns=due_asgns)


@admin.route("/course/<int:cid>/assignments/new", methods=["GET", "POST"])
@is_staff(course_arg='cid')
def new_assignment(cid):
    courses, current_course = get_courses(cid)
    form = forms.AssignmentForm()
    if form.validate_on_submit():
        model = Assignment(course_id=cid, creator_id=current_user.id)
        form.populate_obj(model)
        db.session.add(model)
        db.session.commit()

        flash("Assignment created successfully.", "success")
        return redirect(url_for(".course_assignments", cid=cid))

    return render_template('staff/course/assignment.new.html', form=form,
                           courses=courses, current_course=current_course)


@admin.route("/course/<int:cid>/assignments/<int:aid>",
             methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def assignment(cid, aid):
    courses, current_course = get_courses(cid)
    assgn = Assignment.query.filter_by(id=aid, course_id=cid).one()
    # Convert TZ to Pacific
    assgn.due_date = convert_to_pacific(assgn.due_date)
    assgn.lock_date = convert_to_pacific(assgn.lock_date)
    form = forms.AssignmentUpdateForm(obj=assgn)

    stats = Assignment.assignment_stats(assgn.id)

    if assgn.course != current_course:
        return abort(401)

    if form.validate_on_submit():
        form.populate_obj(assgn)
        db.session.commit()

    return render_template('staff/course/assignment.html', assignment=assgn,
                           form=form, courses=courses, stats=stats,
                           current_course=current_course)

@admin.route("/course/<int:cid>/assignments/<int:aid>/scores")
@is_staff(course_arg='cid')
def export_scores(cid, aid):
    courses, current_course = get_courses(cid)
    assign = Assignment.query.filter_by(id=aid, course_id=cid).one()
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
            for submitter in submitters:
                data = {'email': submitter.user.email,
                        'time': score.backup.created,
                        'is_late': score.backup.is_late,
                        'group': group}
                data.update(submitter.export)
                data.update(score.export)
                csv_writer.writerow(data)
            yield csv_file.getvalue()

    file_name = "{}.csv".format(assign.name.replace('/', '-'))
    disposition = 'attachment; filename={}'.format(file_name)

    # TODO: Remove. For local performance testing.
    # return render_template('staff/index.html', data=list(generate_csv()))
    return Response(stream_with_context(generate_csv()), mimetype='text/csv',
                    headers={'Content-Disposition': disposition})


@admin.route("/course/<int:cid>/enrollment", methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def enrollment(cid):
    courses, current_course = get_courses(cid)
    single_form = forms.EnrollmentForm(prefix="single")
    if single_form.validate_on_submit():
        email, role = single_form.email.data, single_form.role.data
        Enrollment.enroll_from_form(cid, single_form)
        flash("Added {email} as {role}".format(
            email=email, role=role), "success")

    query = request.args.get('query', '').strip()
    page = request.args.get('page', 1, type=int)

    students = None
    if query:
        find_student = User.query.filter_by(email=query)
        student = find_student.first()
        if student:
            students = (Enrollment.query
                        .filter_by(course_id=cid, role=STUDENT_ROLE,
                                   user_id=student.id)
                        .paginate(page=page, per_page=1))
        else:
            flash("No student found with email {}".format(query), "warning")
    if not students:
        students = (Enrollment.query
                    .filter_by(course_id=cid, role=STUDENT_ROLE)
                    .paginate(page=page, per_page=5))

    staff = Enrollment.query.filter(Enrollment.course_id == cid,
                                    Enrollment.role.in_(STAFF_ROLES)).all()

    return render_template('staff/course/enrollment.html',
                           enrollments=students, staff=staff, query=query,
                           single_form=single_form,
                           courses=courses,
                           current_course=current_course)


@admin.route("/course/<int:cid>/enrollment/batch",
             methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def batch_enroll(cid):
    courses, current_course = get_courses(cid)
    batch_form = forms.BatchEnrollmentForm()
    if batch_form.validate_on_submit():
        new, updated = Enrollment.enroll_from_csv(cid, batch_form)
        msg = "Added {new}, Updated {old} students".format(new=new, old=updated)
        flash(msg, "success")
        return redirect(url_for(".enrollment", cid=cid))

    return render_template('staff/course/enrollment.batch.html',
                           batch_form=batch_form,
                           courses=courses,
                           current_course=current_course)
