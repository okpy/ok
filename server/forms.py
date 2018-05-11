from flask import request
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
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
from server.models import Assignment, User, Client, Course, Message, CanvasCourse
from server.constants import (SCORE_KINDS, COURSE_ENDPOINT_FORMAT,
                              TIMEZONE, STUDENT_ROLE, ASSIGNMENT_ENDPOINT_FORMAT,
                              COMMON_LANGUAGES, ROLE_DISPLAY_NAMES,
                              OAUTH_OUT_OF_BAND_URI)

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
    name = StringField('Endpoint (example: cal/cs61a/fa16/proj01)',
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
    continuous_autograding = BooleanField('Send Submissions to Autograder Immediately',
                                         [validators.optional()])
    uploads_enabled = BooleanField('Enable Web Uploads', default=True,
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
                'The endpoint should be of the form {0}/<name>'.format(self.course.offering))
            return False

        # If the name is changed, ensure assignment offering is unique
        assgn = Assignment.query.filter_by(name=self.name.data).first()
        if assgn:
            self.name.errors.append('That endpoint already exists')
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


class EnrollmentExportForm(BaseForm):
    roles = MultiCheckboxField('Roles', choices=ROLE_DISPLAY_NAMES.items(),
            validators=[validators.required()])

    def validate(self):
        if not super().validate():
            return False
        return all(role in ROLE_DISPLAY_NAMES.keys() for role in self.roles.data)


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

class SectionAssignmentForm(BaseForm):
    name = StringField('Name', validators=[validators.optional()])
    email = EmailField('Email',
                       validators=[validators.required(), validators.email()])
    sid = StringField('SID', validators=[validators.optional()])
    secondary = StringField('Secondary Auth (e.g Username)',
                            validators=[validators.optional()])
    section = IntegerField('Section',
                          validators=[validators.required(), validators.NumberRange(min=0)])
    role = SelectField('Role', default=STUDENT_ROLE,
                       choices=ROLE_DISPLAY_NAMES.items())

class VersionForm(BaseForm):
    current_version = StringField('Current Version',
                                 validators=[validators.required()])
    download_link = StringField('Download Link',
                                validators=[validators.required(), validators.url()])

    def validate(self):
        if not super().validate():
            return False
        if not utils.check_url(self.download_link.data):
            self.download_link.errors.append('Invalid URL')
            return False
        return True


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
            elif not re.match(r"[^@]+@[^@]+\.[^@]+", row[0]):
                # checking for email
                # https://stackoverflow.com/questions/8022530/python-check-for-valid-email-address
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

class CheckpointCreditForm(GradeForm):
    """ Gives credit to all students who submitted before a specific time. """
    deadline = DateTimeField('Checkpoint Date', validators=[validators.required()],
                             description="Award points to all submissions before this time")
    include_backups = BooleanField('Include Backups', default=True,
                                   description='Include backups (as well as submissions)')
    grade_backups = BooleanField('Grade Backups', default=False,
                                   description='Grade backups using the autograder')
    kind = SelectField('Kind', choices=[(c, c.title()) for c in SCORE_KINDS if 'checkpoint' in c.lower()],
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

class BatchCSVScoreForm(SubmissionTimeForm):
    use_csv = RadioField(
        'Upload Scores Using',
        choices=[
            ('csv', 'CSV'),
            ('text', 'Email, Score'),
            ('emails', 'Emails Only')
        ],
        default='csv',
        validators=[validators.required()],
    )

    # CSV Fields
    upload_files = FileField('csv', validators=[
        FileAllowed(['csv'], 'csvs only!')])
    email = StringField('Email Label Name')
    score = StringField('Score Label Name')

    # Text Fields
    textarea = TextAreaField('text')

    # Email only
    emails_area = TextAreaField('emails only')
    score_amount = DecimalField('Score (to assign to each email)', default=1)

    # Common
    kind = SelectField('Kind', choices=[(c, c.title()) for c in SCORE_KINDS],
                validators=[validators.required()])

    message = StringField('Message', validators=[validators.required()])
    error = None

    def is_email(self, s):
        email_re = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")
        return email_re.fullmatch(s) is not None

    def is_number(self, s):
        try:
            return bool(s and float(s))
        except Exception:
            return False

    def validate(self):

        if not super().validate():
            return False

        try:
            if self.use_csv.data == 'csv':
                self.input_field = self.upload_files
                assert self.upload_files.data, 'CSV file is required'
                assert self.email.data, 'Email label name is required'
                assert self.score.data, 'Score label name is required'
                self.labels = {'email': self.email.data, 'score': self.score.data}
                rows = self.upload_files.data.read().decode('utf-8').splitlines()
            elif self.use_csv.data == 'text':
                self.input_field = self.textarea
                assert self.textarea.data, 'textarea cannot be empty'
                self.labels = {'email': 'Email', 'score': 'Score'}
                rows = self.textarea.data.splitlines()
                rows.insert(0, 'Email,Score')
            else:  # emails only
                self.input_field = self.emails_area
                assert self.emails_area.data, 'Emails textarea cannot be empty'
                assert self.score_amount.data, 'Score field cannot be empty'
                self.labels = {'email': 'Email', 'score': 'Score'}
                emails = [email for email in re.split('[, \r\n\t]+', self.emails_area.data) if email]
                scores = [self.score_amount.data] * len(emails)
                rows = ['{},{}'.format(*fields) for fields in zip(emails, scores)]
                rows.insert(0, 'Email,Score')

            rows = list(csv.DictReader(rows))

            self.parsed = []
            self.invalid = []

            for linenum, row in enumerate(rows, 1):
                if self.labels.values() & row.keys():
                    email_label = self.labels['email'].strip()
                    score_label = self.labels['score'].strip()

                    email, score = row[email_label], row[score_label]

                    if self.is_email(email) and self.is_number(score):
                        score = (score and float(score)) or 0
                        self.parsed.append({'email': email, 'score': score})
                        continue

                self.invalid.append(linenum)

        except AssertionError as e:
            logging.error(e)
            self.error = str(e)
            self.input_field.errors.append(self.error)
            return False
        except KeyError as e:
            missing = str(e).lstrip('KeyError: ')
            self.error = 'Column name "{}" doesn\'t exist.'.format(missing)
            self.input_field.errors.append(self.error)
            return False
        except csv.Error as e:
            logging.error(e)
            self.error = "We couldn't parse the CSV; Check to make sure it's formatted properly."
            self.input_field.errors.append(self.error)
            return False

        return True


class ExtensionForm(SubmissionTimeForm):
    assignment_id = SelectField('Assignment', coerce=int, validators=[validators.required()])
    expires = DateTimeField('Extension Expiry', validators=[validators.required()])
    email = EmailField('Student Email',
                       validators=[validators.required(), validators.email()])
    reason = StringField('Justification',
                         description="Why are you granting this extension?",
                         validators=[validators.optional()])

    def validate(self):
        check_validate = super(ExtensionForm, self).validate()
        # if our validators do not pass
        if not check_validate:
            return False
        user = User.lookup(self.email.data)
        if not user:
            message = "{} does not have an OK account".format(self.email.data)
            self.email.errors.append(message)
            return False
        return check_validate

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
        'Allowed Redirect URIs',
        description='Comma-separated list. Redirects to localhost and 127.0.0.1 are always allowed. '
            'Redirects to {} will display the code in the browser instead of redirecting.'.format(OAUTH_OUT_OF_BAND_URI))

    default_scopes = CommaSeparatedField(
        'Default Scope',
        description='Comma-separated list. Valid scopes are "email" and "all".')

    def validate(self):
        # if our validators do not pass
        if not super(ClientForm, self).validate():
            return False
        existing_client = Client.query.filter_by(client_id=self.client_id.data).first()
        if existing_client:
            self.client_id.errors.append('That client ID already exists')
            return False
        return True


class EditClientForm(ClientForm):
    active = BooleanField(
            'Active',
            description='Whether this client is active and available to be used.',
            default=False,
            )
    owner = EmailField(
        'Owner Email',
        description='''Must be a valid email of OK account with 
            staff access in some course. (Current owner will lose access if changed.)''',
        validators=[validators.optional(), validators.email()]
    )
    user = HiddenField(
        description="Do not fill out or render.",
        validators=[validators.optional()]
    )
    user_id = HiddenField(
        description="Do not fill out or render.",
        validators=[validators.optional()]
    )
    roll_secret = BooleanField(
        'Change the secret?',
        description='''Should the secret be changed? If checked,
            the new value will appear after submission''',
        default=False)
    client_secret = HiddenField(
        'Placeholder for secret',
        description="Do not fill out or render.",
        validators=[validators.optional()])

    def __init__(self, obj=None, **kwargs):
        self.obj = obj
        super(ClientForm, self).__init__(obj=obj, **kwargs)

    def validate(self):
        is_error = False
        # if our validators do not pass
        if not super(ClientForm, self).validate():
            is_error = True
        if self.client_id.data != self.obj.client_id:
            existing_client = Client.query.filter_by(client_id=self.client_id.data).first()
            if existing_client:
                self.client_id.errors.append('That client ID already exists')
                is_error = True
        if self.owner.data != self.obj.owner:
            user = User.query.filter_by(email=self.owner.data).one_or_none()
            if not user:
                self.owner.errors.append("Email does not exist.")
                is_error = True
            elif not user.is_staff():
                self.owner.errors.append('New owner must be a some course staff member.')
                is_error = True
            elif not is_error:
                # New user is valid so populate necessary attributes to update model
                self.user.data = user
                self.user_id.data = user.id
        elif not is_error:
            # User isn't changing set to None to avoid overwriting in model
            self.user.data = None
            self.user_id.data = None
        return not is_error

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
            self.offering.errors.append(('The name should look like univ/course101/semYY where "sem" is one of (fa, su, sp, au, wi)'))
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

class EffortGradingForm(BaseForm):
    full_credit = DecimalField('Full Credit (in points)',
                    validators=[
                        validators.required(),
                        validators.number_range(min=0, message="Points cannot be negative.")],
                    description="Points received for showing sufficient effort on an assignment.")
    required_questions = IntegerField('Required Questions',
                    validators=[
                        validators.number_range(min=0, message="Questions cannot be negative.")],
                    description="Number of required questions on the assignment.")
    late_multiplier = DecimalField('Late Multiplier (as a decimal)',
                    validators=[
                        validators.number_range(min=0, max=1, message="Multiplier must be between 0 and 1")],
                    default=0.0,
                    description="Decimal ratio that is multiplied to the final score of a late submission.")

class ExportGradesForm(BaseForm):
    included = MultiCheckboxField('Included Assignments', description='Assignments with any published scores are checked by default')

    def __init__(self, assignments):
        super().__init__()

        self.included.choices = [(str(a.id), a.display_name) for a in assignments]
        self.included.data = [str(a.id) for a in assignments if a.published_scores]

    def validate(self):
        return super().validate() and len(self.included.data) > 0


########
# Jobs #
########

class TestJobForm(BaseForm):
    should_fail = BooleanField('Divide By Zero', default=False)
    make_file = BooleanField('Create a file', default=True)
    duration = IntegerField('Duration (seconds)', default=2)

class MossSubmissionForm(BaseForm):
    moss_userid = StringField('Moss User ID', default='619379711',
                              validators=[validators.required()])
    file_regex = StringField('Regex for submitted files', default='.*',
                             validators=[validators.required()])
    language = SelectField('Programming Language', choices=[(pl, pl) for pl in COMMON_LANGUAGES])
    review_threshold = DecimalField('Review Threshold', default=0.30,
        description="Results with this similarity percentage or higher will be tagged for review.")
    num_results = IntegerField('Number of Results', default=250,
        description="Number of similarity results to request from Moss.")

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
                               description="The strings '{repo}' and '{author}' will be replaced with the appropriate value")

class EmailScoresForm(BaseForm):
    subject = StringField('Subject', validators=[validators.required()])
    body = TextAreaField('Body', validators=[validators.required()],
                       description="Is there anything the students need to know about the scores?",
                       default="An instructor has published scores. If you have questions, please contact the course staff")
    reply_to = EmailField('Reply To Address', default="no-reply@okpy.org",
                          description="What email should replies be sent to?",
                          validators=[validators.required(), validators.email()])
    dry_run = BooleanField('Dry Run Mode', default=True,
                           description="Don't send emails to students; instead, send a few examples to your email.")
    kinds = MultiCheckboxField(
        'Scores Tags',
        choices=[(kind, kind.title()) for kind in SCORE_KINDS],
    )


class ExportAssignment(BaseForm):
    anonymize = BooleanField('Anonymize', default=False,
                             description="Enable to remove identifying information from submissions")

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
