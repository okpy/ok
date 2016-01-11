from flask_wtf import Form
from wtforms import TextField, DateTimeField, BooleanField, IntegerField
from wtforms import validators

import datetime as dt
# from wtforms.ext.sqlalchemy.orm import model_form
from .models import Assignment
import pytz


def strip_whitespace(input):
    if hasattr(input, "strip"):
        return input.strip()
    else:
        return input


def convert_to_utc(date):
    # TODO Not sure if 100 TZ aware. Unit test.
    return pytz.utc.localize(date)


class AssignmentForm(Form):
    display_name = TextField(u'Display Name',
                             [validators.required()])
    name = TextField(u'Offering', filters=[strip_whitespace],
                     validators=[validators.required()])
    due_date = DateTimeField(u'Due Date (Pacific Time)',
                             filters=[convert_to_utc],
                             default=dt.datetime.now,
                             validators=[validators.required()])
    lock_date = DateTimeField(u'Lock Date (UTC)',
                              filters=[convert_to_utc],
                              default=dt.datetime.now,
                              validators=[validators.required()])
    max_group_size = IntegerField(u'Max Group Size', default=1,
                                  validators=[validators.required()])
    url = TextField(u'URL', [validators.optional()])
    revisions = BooleanField(u'Enable Revisions', default=False,
                             validators=[validators.optional()])
    autograding_key = TextField(u'Autograder Key', [validators.optional()])
    # TODO Convert to UTC time.

    def validate(self):
        check_validate = super(AssignmentForm, self).validate()

        # if our validators do not pass
        if not check_validate:
            return False

        # Ensure assignment offering is unique
        assgn = Assignment.query.filter_by(name=self.name.data).first()
        if assgn:
            self.name.errors.append('That offering already exists')
            return False
        return True
