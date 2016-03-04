from flask_wtf import Form
from wtforms import StringField, DateTimeField, BooleanField, IntegerField, \
    SelectField, TextAreaField, SubmitField, HiddenField, validators

from wtforms.widgets.core import HTMLString, html_params, escape
from wtforms.fields.html5 import EmailField

import datetime as dt
# from wtforms.ext.sqlalchemy.orm import model_form
from .models import Assignment
from server.constants import VALID_ROLES

import pytz
import csv
import logging

def strip_whitespace(value):
    if value and hasattr(value, "strip"):
        return value.strip()
    else:
        return value


def convert_to_utc(date):
    # TODO Not sure if 100% TZ aware. Unit test.
    return pytz.utc.localize(date)

class BaseForm(Form):
    class Meta:
        def bind_field(self, form, unbound_field, options):
            filters = unbound_field.kwargs.get('filters', [])
            field_type = type(unbound_field)
            if field_type == StringField:
                filters.append(strip_whitespace)
            elif field_type == DateTimeField:
                filters.append(convert_to_utc)
            return unbound_field.bind(form=form, filters=filters, **options)


class AssignmentForm(BaseForm):
    display_name = StringField(u'Display Name',
                               validators=[validators.required()])
    name = StringField(u'Offering', validators=[validators.required()])
    due_date = DateTimeField(u'Due Date (Pacific Time)',
                             default=dt.datetime.now,
                             validators=[validators.required()])
    lock_date = DateTimeField(u'Lock Date (Pacific Time)',
                              default=dt.datetime.now,
                              validators=[validators.required()])
    max_group_size = IntegerField(u'Max Group Size', default=1,
                                  validators=[validators.required()])
    url = StringField(u'URL',
                      validators=[validators.optional(), validators.url()])
    revisions = BooleanField(u'Enable Revisions', default=False,
                             validators=[validators.optional()])
    autograding_key = StringField(u'Autograder Key', [validators.optional()])

    def validate(self):
        check_validate = super(AssignmentForm, self).validate()

        # if our validators do not pass
        if not check_validate:
            return False

        # If the name is changed , ensure assignment offering is unique
        assgn = Assignment.query.filter_by(name=self.name.data).first()
        if assgn:
            self.name.errors.append('That offering already exists')
            return False
        return True

class AssignmentUpdateForm(AssignmentForm):
    def validate(self):
        return super(AssignmentForm, self).validate()


class EnrollmentForm(BaseForm):
    name = StringField(u'Name', validators=[validators.optional()])
    email = EmailField(u'Email',
                       validators=[validators.required(), validators.email()])
    sid = StringField(u'SID', validators=[validators.optional()])
    secondary = StringField(u'Secondary Auth (e.g Username)',
                            validators=[validators.optional()])
    role = SelectField(u'Role',
                       choices=[(r, r.capitalize()) for r in VALID_ROLES])

class BatchEnrollmentForm(BaseForm):
    csv = TextAreaField(u'Email, Name, SID, Course Login, Notes')

    def validate(self):
        check_validate = super(BatchEnrollmentForm, self).validate()
        # if our validators do not pass
        if not check_validate:
            return False
        try:
            rows = self.csv.data.splitlines()
            self.csv.parsed = list(csv.reader(rows))
        except csv.error as e:
            logging.error(e)
            self.csv.errors.append(['The CSV could not be parsed'])
            return False

        for row in self.csv.parsed:
            if len(row) != 5:
                err = "{} did not have 5 columns".format(row)
                self.csv.errors.append(err)
                return False
            if not row[0]:
                err = "{} did not have an email".format(row)
                self.csv.errors.append(err)
                return False
            elif "@" not in row[0]:
                # TODO : Better email check.
                err = "{} is not a valid email".format(row[0])
                self.csv.errors.append(err)
                return False
        return True

class CSRFForm(BaseForm):
    pass
