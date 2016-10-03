from flask_wtf import Form
from flask_wtf.file import FileField, FileRequired
from wtforms import (StringField, DateTimeField, BooleanField, IntegerField,
                     SelectField, TextAreaField, DecimalField, HiddenField,
                     SelectMultipleField, Field, widgets, validators)
from flask_wtf.html5 import EmailField

import pytz
import datetime as dt

from server import utils
from server.models import Assignment, Course
from server.constants import (VALID_ROLES, GRADE_TAGS, COURSE_ENDPOINT_FORMAT,
                              TIMEZONE, STUDENT_ROLE, ASSIGNMENT_ENDPOINT_FORMAT)

import csv
import logging

def strip_whitespace(value):
    if value and hasattr(value, "strip"):
        return value.strip()
    else:
        return value

class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

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

class BaseForm(Form):

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
                       choices=[(r, r.title()) for r in VALID_ROLES])


class VersionForm(BaseForm):
    current_version = EmailField('Current Version',
                                 validators=[validators.required()])
    download_link = StringField('Download Link',
                                validators=[validators.required(), validators.url()])


class BatchEnrollmentForm(BaseForm):
    csv = TextAreaField('Email, Name, SID, Course Login, Section')
    role = SelectField('Role', default=STUDENT_ROLE,
                       choices=[(r, r.title()) for r in VALID_ROLES])

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
    score = DecimalField('Score', validators=[validators.required()])
    message = TextAreaField('Message', validators=[validators.required()])
    kind = SelectField('Kind', choices=[(c, c.title()) for c in GRADE_TAGS],
                       validators=[validators.required()])

class CompositionScoreForm(GradeForm):
    score = SelectField('Composition Score',
                        choices=[('0', '0'), ('1', '1'), ('2', '2')],
                        validators=[validators.required()])
    kind = HiddenField('Score', default="composition",
                       validators=[validators.required()])


class CreateTaskForm(BaseForm):
    kind = SelectField('Kind', choices=[(c, c.title()) for c in GRADE_TAGS],
                       validators=[validators.required()], default="composition")
    staff = MultiCheckboxField('Assigned Staff', choices=[],
                               validators=[validators.required()])
    only_unassigned = BooleanField('Ignore submissions that already have a grader',
                                   default=False)

class AutogradeForm(BaseForm):
    description = """Run this command in the terminal under any assignment folder: python3 ok --get-token"""
    token = StringField('Access Token', description=description,
                        validators=[validators.optional()])
    autograder_id = StringField('Autograder Assignment ID',
                                validators=[validators.required()])
    autopromote = BooleanField('Backup Autopromotion',
                               description="If an enrolled student does not have a submission, this will grade their latest submission before the deadline")

class UploadSubmissionForm(BaseForm):
    upload_files = FileField('Submission Files', [FileRequired()])
    flag_submission = BooleanField('Flag this submission for grading',
                                   default=False)

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

########
# Jobs #
########

class TestJobForm(BaseForm):
    should_fail = BooleanField('Divide By Zero', default=False)
    duration = IntegerField('Duration (seconds)', default=2)

class MossSubmissionForm(BaseForm):
    valid_languages = ['python', 'java', 'c', 'scheme', 'lisp', 'javascript']
    moss_userid = StringField('Your MOSS User ID',
                              validators=[validators.required()])
    file_regex = StringField('Regex for submitted files', default='.*',
                             validators=[validators.required()])
    language = SelectField('Language', choices=[(pl, pl) for pl in valid_languages])
