from flask import request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired
import requests.exceptions
from wtforms import (StringField, DateTimeField, BooleanField, IntegerField,
                     SelectField, TextAreaField, DecimalField, HiddenField,
                     SelectMultipleField, RadioField, Field,
                     widgets, validators)
from wtforms.fields.html5 import EmailField

import datetime as dt
import pytz
import re

from server import utils
import server.canvas.api as canvas_api
from server.models import Assignment, Course, Message, CanvasCourse
from server.constants import (SCORE_KINDS, COURSE_ENDPOINT_FORMAT,
                              TIMEZONE, STUDENT_ROLE, ASSIGNMENT_ENDPOINT_FORMAT,
                              COMMON_LANGUAGES, ROLE_DISPLAY_NAMES)

import csv
import logging

def strip_whitespace(value):
    if value and hasattr(value, "strip"):
        return value.strip()
    else:
        return value

class OptionalUnless(validators.Optional):
    '''A validator which makes a field required only if another field is set to
    a given value.

    Inspired by http://stackoverflow.com/a/8464478
    '''
    def __init__(self, other_field_name, other_field_value, *args, **kwargs):
        self.other_field_name = other_field_name
        self.other_field_value = other_field_value
        super().__init__(*args, **kwargs)

    def __call__(self, form, field):
        other_field = form._fields.get(self.other_field_name)
        if other_field is None:
            raise Exception('no field named "%s" in form' % self.other_field_name)
        if other_field.data != self.other_field_value:
            super().__call__(form, field)

class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class BackupUploadField(FileField):
    def upload_backup_files(self, backup):
        """Update a Backup's attributes based on form contents. If successful,
        return True; otherwise, add errors to the form and return False.
        """
        assignment = backup.assignment
        templates = assignment.files

        files = {}
        for upload in request.files.getlist(self.name):
            data = upload.read()
            if len(data) > 15 * 1024 * 1024:  # file is too large (over 15 MB)
                self.errors.append(
                    '{} is larger than the maximum file size '
                    'of 15MB'.format(upload.filename))
                return False
            try:
                files[upload.filename] = str(data, 'utf-8')
            except UnicodeDecodeError:
                self.errors.append(
                    '{} is not a UTF-8 text file'.format(upload.filename))
                return False
        template_files = assignment.files or []
        missing = [
            template for template in template_files
                if template not in files
        ]
        if missing:
            self.errors.append(
                'Missing files: {}. The following files are required: {}'
                   .format(', '.join(missing), ', '.join(templates)))
            return False

        message = Message(kind='file_contents', contents=files)
        backup.messages.append(message)
        return True

class CommaSeparatedField(Field):
    widget = widgets.TextInput()

    def _value(self):
        if self.data:
            return ', '.join(self.data)
        else:
            return ''

    def process_formdata(self, valuelist):
        if valuelist:
            self.data = [x.strip() for x in valuelist[0].split(',')]
        else:
            self.data = []

class BaseForm(FlaskForm):

    class Meta:

        def bind_field(self, form, unbound_field, options):
            filters = unbound_field.kwargs.get('filters', [])
            field_type = type(unbound_field)
            if field_type == StringField:
                filters.append(strip_whitespace)
            return unbound_field.bind(form=form, filters=filters, **options)


class AssignmentForm(BaseForm):

    def __init__(self, course, obj=None, **kwargs):
        self.course = course
        self.obj = obj
        super(AssignmentForm, self).__init__(obj=obj, **kwargs)
        if obj:
            if obj.due_date == self.due_date.data:
                self.due_date.data = utils.local_time_obj(obj.due_date, course)
            if obj.lock_date == self.lock_date.data:
                self.lock_date.data = utils.local_time_obj(
                    obj.lock_date, course)

    display_name = StringField('Display Name',
                               validators=[validators.required()])
    name = StringField('Offering (example: cal/cs61a/fa16/proj01)',
                       validators=[validators.required()])
    due_date = DateTimeField('Due Date (Course Time)',
                             validators=[validators.required()])
    lock_date = DateTimeField('Lock Date (Course Time)',
                              validators=[validators.required()])
    max_group_size = IntegerField('Max Group Size',
                                  default=1,
                                  validators=[validators.InputRequired(),
                                              validators.number_range(min=1)])
    url = StringField('URL',
                      validators=[validators.optional(), validators.url()])
    revisions_allowed = BooleanField('Enable Revisions', default=False,
                                     validators=[validators.optional()])
    autograding_key = StringField('Autograder Key', [validators.optional()])
    uploads_enabled = BooleanField('Enable Web Uploads', default=False,
                                   validators=[validators.optional()])
    upload_info = StringField('Upload Instructions',
                              validators=[validators.optional()])
    visible = BooleanField('Visible On Student Dashboard', default=True)
    autograding_key = StringField('Autograder Key',
                                  validators=[validators.optional()])

    def populate_obj(self, obj):
        """ Updates obj attributes based on form contents. """

        super(AssignmentForm, self).populate_obj(obj)
        obj.due_date = utils.server_time_obj(self.due_date.data, self.course)
        obj.lock_date = utils.server_time_obj(self.lock_date.data, self.course)

    def validate(self):
        check_validate = super(AssignmentForm, self).validate()

        # if our validators do not pass
        if not check_validate:
            return False

        # Ensure the name has the right format:
        is_valid_endpoint = utils.is_valid_endpoint(self.name.data,
                                                    ASSIGNMENT_ENDPOINT_FORMAT)
        has_course_endpoint = self.name.data.startswith(self.course.offering)

        if not has_course_endpoint or not is_valid_endpoint:
            self.name.errors.append(
                'The name should be of the form {0}/<name>'.format(self.course.offering))
            return False

        # If the name is changed, ensure assignment offering is unique
        assgn = Assignment.query.filter_by(name=self.name.data).first()
        if assgn:
            self.name.errors.append('That offering already exists')
            return False
        return True


class AssignmentUpdateForm(AssignmentForm):

    def validate(self):
        # if our validators do not pass
        if not super(AssignmentForm, self).validate():
            return False

        # Ensure the name has the right format:
        is_valid_endpoint = utils.is_valid_endpoint(self.name.data,
                                                    ASSIGNMENT_ENDPOINT_FORMAT)
        has_course_endpoint = self.name.data.startswith(self.course.offering)

        if not has_course_endpoint or not is_valid_endpoint:
            self.name.errors.append(
                'The name should be of the form {0}/<name>'.format(self.course.offering))
            return False

        assgn = Assignment.query.filter_by(name=self.name.data).first()
        if assgn and (self.obj and assgn.id != self.obj.id):
            self.name.errors.append('That offering already exists.')
            return False
        return True


class AssignmentTemplateForm(BaseForm):
    template_files = FileField('Template Files', [FileRequired()])


class EnrollmentForm(BaseForm):
    name = StringField('Name', validators=[validators.required()])
    email = EmailField('Email',
                       validators=[validators.required(), validators.email()])
    sid = StringField('SID', validators=[validators.optional()])
    secondary = StringField('Secondary Auth (e.g Username)',
                            validators=[validators.optional()])
    section = StringField('Section',
                          validators=[validators.optional()])
    role = SelectField('Role', default=STUDENT_ROLE,
                       choices=ROLE_DISPLAY_NAMES.items())


class VersionForm(BaseForm):
    current_version = EmailField('Current Version',
                                 validators=[validators.required()])
    download_link = StringField('Download Link',
                                validators=[validators.required(), validators.url()])


class BatchEnrollmentForm(BaseForm):
    csv = TextAreaField('Email, Name, SID, Course Login, Section')
    role = SelectField('Role', default=STUDENT_ROLE,
                       choices=ROLE_DISPLAY_NAMES.items())

    def validate(self):
        check_validate = super(BatchEnrollmentForm, self).validate()
        # if our validators do not pass
        if not check_validate:
            return False
        try:
            rows = self.csv.data.splitlines()
            self.csv.parsed = list(csv.reader(rows))
        except csv.Error as e:
            logging.error(e)
            self.csv.errors.append(['The CSV could not be parsed'])
            return False

        for row in self.csv.parsed:
            if len(row) != 5:
                err = "{0} did not have 5 columns".format(row)
                self.csv.errors.append(err)
                return False
            if not row[0]:
                err = "{0} did not have an email".format(row)
                self.csv.errors.append(err)
                return False
            elif "@" not in row[0]:
                # TODO : Better email check.
                err = "{0} is not a valid email".format(row[0])
                self.csv.errors.append(err)
                return False
        return True


class CSRFForm(BaseForm):
    pass


class GradeForm(BaseForm):
    score = DecimalField('Score', validators=[validators.InputRequired()])
    message = TextAreaField('Message', validators=[validators.required()])
    kind = SelectField('Kind', choices=[(c, c.title()) for c in SCORE_KINDS],
                       validators=[validators.required()])

class CompositionScoreForm(GradeForm):
    score = SelectField('Composition Score',
                        choices=[('0', '0'), ('1', '1'), ('2', '2')],
                        validators=[validators.required()])
    kind = HiddenField('Score', default="composition",
                       validators=[validators.required()])


class CreateTaskForm(BaseForm):
    kind = SelectField('Kind', choices=[(c, c.title()) for c in SCORE_KINDS],
                       validators=[validators.required()], default="composition")
    staff = MultiCheckboxField('Assigned Staff', choices=[],
                               validators=[validators.required()])

class UploadSubmissionForm(BaseForm):
    upload_files = BackupUploadField('Submission Files', [FileRequired()])

class SubmissionTimeForm(BaseForm):
    submission_time = RadioField(
        'Custom submission time',
        choices=[
            ('none', 'Backup creation time'),
            ('deadline', 'At deadline'),
            ('early', 'One day early'),
            ('other', 'Other: '),
        ],
        default='none',
        validators=[validators.required()],
    )
    custom_submission_time = DateTimeField(
        validators=[OptionalUnless('submission_time', 'other')])

    def get_submission_time(self, assignment):
        choice = self.submission_time.data
        if choice == 'none':
            return None
        elif choice == 'deadline':
            return (assignment.due_date
                - dt.timedelta(seconds=1))
        elif choice == 'early':
            return (assignment.due_date
                - dt.timedelta(days=1, seconds=1))
        elif choice == 'other':
            return utils.server_time_obj(
                self.custom_submission_time.data,
                assignment.course,
            )
        else:
            raise Exception('Unknown submission time choice {}'.format(choice))

    def set_submission_time(self, backup):
        assignment = backup.assignment
        time = backup.custom_submission_time
        if time is None:
            self.submission_time.data = 'none'
        elif time == assignment.due_date - dt.timedelta(seconds=1):
            self.submission_time.data = 'deadline'
        elif time == assignment.due_date - dt.timedelta(days=1, seconds=1):
            self.submission_time.data = 'early'
        else:
            self.submission_time.data = 'other'
            self.custom_submission_time.data = utils.local_time_obj(
                time, assignment.course)

class StaffUploadSubmissionForm(UploadSubmissionForm, SubmissionTimeForm):
    pass

class StaffAddGroupFrom(BaseForm):
    description = """Run this command in the terminal under any assignment folder: python3 ok --get-token"""

    email = EmailField('Email',
                       validators=[validators.required(), validators.email()])

class StaffRemoveGroupFrom(BaseForm):
    email = SelectField('Email',
                        validators=[validators.required(), validators.email()])

class ClientForm(BaseForm):
    """ OAuth Client Form """
    name = StringField('Client Name', validators=[validators.required()])
    description = StringField('Description', validators=[validators.optional()])

    client_id = StringField('Client ID', validators=[validators.required()])
    client_secret = StringField(
        'Client Secret',
        description="Save this token in your configuration. You won't be able to see it again.",
        validators=[validators.required()])

    is_confidential = BooleanField(
        'Confidential',
        description='Refresh tokens are only available for "confidential" clients.',
        default=True)

    redirect_uris = CommaSeparatedField(
        'Redirect URIs',
        description='Comma-separated list.')

    default_scopes = CommaSeparatedField(
        'Default Scope',
        description='Comma-separated list. Valid scopes are "email" and "all".')


class NewCourseForm(BaseForm):
    offering = StringField('Offering (example: cal/cs61a/sp16)',
                           validators=[validators.required()])
    institution = StringField('School (e.g. UC Berkeley)',
                           validators=[validators.optional()])
    display_name = StringField('Course Name (e.g CS61A)',
                           validators=[validators.required()])
    website = StringField('Course Website',
                           validators=[validators.optional(), validators.url()])
    active = BooleanField('Activate Course', default=True)
    timezone = SelectField('Course Timezone', choices=[(t, t) for t in pytz.common_timezones],
                           default=TIMEZONE)

    def validate(self):
        # if our validators do not pass
        if not super(NewCourseForm, self).validate():
            return False

        # Ensure the name has the right format:
        if not utils.is_valid_endpoint(self.offering.data, COURSE_ENDPOINT_FORMAT):
            self.offering.errors.append(('The name should like univ/course101/semYY'))
            return False

        course = Course.query.filter_by(offering=self.offering.data).first()
        if course:
            self.offering.errors.append('That offering already exists.')
            return False
        return True

class CourseUpdateForm(BaseForm):
    institution = StringField('School (e.g. UC Berkeley)',
                              validators=[validators.optional()])
    display_name = StringField('Course Name (e.g CS61A)',
                               validators=[validators.required()])
    website = StringField('Course Website',
                          validators=[validators.optional(), validators.url()])
    active = BooleanField('Activate Course', default=True)
    timezone = SelectField('Course Timezone', choices=[(t, t) for t in pytz.common_timezones])

class PublishScores(BaseForm):
    published_scores = MultiCheckboxField(
        'Published Scores',
        choices=[(kind, kind.title()) for kind in SCORE_KINDS],
    )


########
# Jobs #
########

class TestJobForm(BaseForm):
    should_fail = BooleanField('Divide By Zero', default=False)
    duration = IntegerField('Duration (seconds)', default=2)

class MossSubmissionForm(BaseForm):
    moss_userid = StringField('Your MOSS User ID',
                              validators=[validators.required()])
    file_regex = StringField('Regex for submitted files', default='.*',
                             validators=[validators.required()])
    language = SelectField('Language', choices=[(pl, pl) for pl in COMMON_LANGUAGES])

class GithubSearchRecentForm(BaseForm):
    access_token = StringField('Github Access Token',
                               description="Get a token at https://github.com/settings/tokens",
                               validators=[validators.required()])
    template_name = StringField('Template File Name',
                                validators=[validators.required()])
    keyword = StringField('Search for lines starting with', default="def ",
                          validators=[validators.required()])
    weeks_past = IntegerField('Limit search to weeks since start of course?', default=12)
    language = SelectField('Language', choices=[(pl, pl) for pl in COMMON_LANGUAGES])
    issue_title = StringField('Issue Title (Optional)', validators=[validators.optional()],
                                default="Academic Integrity - Please Delete This Repository")
    issue_body = TextAreaField('Issue Body (Optional)', validators=[validators.optional()],
                               description="The strings '{repo}' and '{author}' will be replace with the approriate value")

##########
# Canvas #
##########

# e.g. https://bcourses.berkeley.edu/courses/1234567
CANVAS_COURSE_URL_REGEX = r'^https?://(([a-zA-Z0-9-]+\.)+[a-zA-Z0-9-]+)/courses/(\d+)'

class CanvasCourseForm(BaseForm):
    url = StringField('bCourses Course URL', validators=[
        validators.Regexp(CANVAS_COURSE_URL_REGEX, message='Enter a bCourses Course URL'),
    ])
    access_token = StringField('Access Token',
        description='On bCourses, go to Account > Settings > New Access Token',
        validators=[validators.required()],
    )

    def populate_canvas_course(self, canvas_course):
        match = re.search(CANVAS_COURSE_URL_REGEX, self.url.data)
        canvas_course.api_domain = match.group(1)
        canvas_course.external_id = int(match.group(3))
        canvas_course.access_token = self.access_token.data

    def validate_access_token(self, field):
        try:
            canvas_course = CanvasCourse()
            self.populate_canvas_course(canvas_course)
            canvas_api.get_course(canvas_course)
        except requests.exceptions.HTTPError as e:
            field.errors.append('Invalid access token')

class CanvasAssignmentForm(BaseForm):
    external_id = SelectField('bCourses Assignment',
        coerce=int, validators=[validators.required()])
    assignment_id = SelectField('OK Assignment',
        coerce=int, validators=[validators.required()])
    score_kinds = MultiCheckboxField(
        'Scores',
        description='Maximum score from selected score kinds will be uploaded',
        choices=[(kind, kind.title()) for kind in SCORE_KINDS],
        validators=[validators.required()],
    )
