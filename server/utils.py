import csv
import datetime as dt
import logging
import math
from io import StringIO
import os
import random
import re
from urllib.parse import urlparse, urljoin

from flask import render_template, url_for
from hashids import Hashids
import humanize
from oauthlib.common import generate_token
from pynliner import fromString as emailFormat
import pytz
import sendgrid

from server.extensions import cache
from server import constants

sg = sendgrid.SendGridClient(
    os.getenv('SENDGRID_KEY'), None, raise_errors=True)
logger = logging.getLogger(__name__)

# ID hashing configuration.
# DO NOT CHANGE ONCE THE APP IS PUBLICLY AVAILABLE. You will break every
# link with an ID in it.
hashids = Hashids(min_length=6)

def encode_id(id_number):
    return hashids.encode(id_number)

def decode_id(value):
    numbers = hashids.decode(value)
    if len(numbers) != 1:
        raise ValueError('Could not decode hash {0} into ID'.format(value))
    return numbers[0]

# Timezones. Be cautious with using tzinfo argument. http://pytz.sourceforge.net/
# "tzinfo argument of the standard datetime constructors 'does not work'
# with pytz for many timezones."

def local_time(time, course, fmt='%a %m/%d %I:%M %p'):
    """ Format a time string in a course's locale.
    Note that %-I does not perform as expected on Alpine Linux
    """
    return local_time_obj(time, course).strftime(fmt)

def local_time_obj(time, course):
    """ Get a Datetime object in a course's locale from a TZ Aware DT object."""
    if not time.tzinfo:
        time = pytz.utc.localize(time)
    return time.astimezone(course.timezone)

def server_time_obj(time, course):
    """ Convert a datetime object from a course's locale to a UTC
    datetime object.
    """
    if not time.tzinfo:
        time = course.timezone.localize(time)
    # Store using UTC on the server side.
    return time.astimezone(pytz.utc)

def future_time_obj(course, **kwargs):
    """ Get a datetime object representing some timedelta from now with the time
    set at 23:59:59.
    """
    date = course.timezone.localize(dt.datetime.now() + dt.timedelta(**kwargs))
    time = dt.time(hour=23, minute=59, second=59, microsecond=0)
    return dt.datetime.combine(date, time)

def new_due_date(course):
    """ Return a string representing a new due date next week."""
    return future_time_obj(course, weeks=1).strftime(constants.ISO_DATETIME_FMT)

def new_lock_date(course):
    """ Return a string representing a new lock date 8 days from now."""
    return (future_time_obj(course, weeks=1, days=1)
            .strftime(constants.ISO_DATETIME_FMT))

def natural_time(date):
    """ Format a human-readable time difference (e.g. "6 days ago")"""
    if date.tzinfo:
        date = date.astimezone(pytz.utc).replace(tzinfo=None)
    now = dt.datetime.utcnow()
    return humanize.naturaltime(now - date)


def humanize_name(name):
    """ Return a canonical representation of a name in First Last format."""
    if not isinstance(name, str):
        return name
    elif name.upper() == name:
        return " ".join([part.strip().title() for part in name.split(",")][::-1])
    else:
        return " ".join([part.strip() for part in name.split(",")][::-1])


def is_safe_redirect_url(request, target):
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ('http', 'https') and \
        host_url.netloc == redirect_url.netloc

def random_row(query):
    count = query.count()
    if not count:
        return None
    return query.offset(random.randrange(count)).first()


def group_action_email(members, subject, text):
    emails = [m.user.email for m in members]
    return send_email(emails, subject, text)


def invite_email(member, recipient, assignment):
    subject = "{0} group invitation".format(assignment.display_name)
    text = "{0} has invited you to join their group".format(member.email)
    link_text = "Respond to the invitation"
    link = url_for('student.assignment', name=assignment.name, _external=True)
    template = 'email/invite.html'

    send_email(recipient.email, subject, text, template,
               link_text=link_text, link=link)


def send_email(to, subject, body, template='email/notification.html',
               link=None, link_text="Sign in"):
    """ Send an email using sendgrid.
    Usage: send_email('student@okpy.org', 'Hey from OK', 'hi')
    """
    if not link:
        link = url_for('student.index', _external=True)
    html = render_template(template, subject=subject, body=body,
                           link=link, link_text=link_text)
    message = sendgrid.Mail(
        to=to,
        from_name="Okpy.org",
        from_email="no-reply@okpy.org",
        subject=subject,
        html=emailFormat(html),
        text=body)

    try:
        status, msg = sg.send(message)
        return status
    except (sendgrid.SendGridClientError, sendgrid.SendGridServerError,
            TypeError, ValueError):
        logger.error("Could not send email", exc_info=True)
        return

def chunks(l, n):
    """ Divides L into N many chunks, each containing approximately the
    same number of elements. Used for GradingTask distribution.

    Refrence: http://stackoverflow.com/a/9873935

    >>> [len(x) for x in chunks(range(45), 13)]
    [4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 4, 3, 3]
    >>> [len(x) for x in chunks(range(253), 13)]
    [20, 19, 20, 19, 20, 19, 20, 19, 20, 19, 20, 19, 19]
    >>> [len(i) for i in chunks(range(56), 3)]
    [19, 19, 18]
    >>> [len(i) for i in chunks(range(55), 5)]
    [11, 11, 11, 11, 11]
    """
    length = len(l)
    prev_index = 0
    for i in range(1, n + 1):
        index = math.ceil((i / n) * length)
        yield l[prev_index:index]
        prev_index = index


def generate_csv(query, items, selector_fn):
    """ Generate csv export of scores for assignment.
        selector_fn: 1 arg function that returns a list of dictionaries
    """
    # Yield Column Info as first row
    yield ','.join(items) + '\n'
    for row in query:
        csv_file = StringIO()
        csv_writer = csv.DictWriter(csv_file, fieldnames=items)
        export_values = selector_fn(row)
        data = {}
        for dict in export_values:
            data.update(dict)
        csv_writer.writerow(data)
        yield csv_file.getvalue()

def is_valid_endpoint(endpoint, valid_format):
    """ Validates an endpoint name against a regex pattern VALID_FORMAT. """
    r = re.compile(valid_format)
    is_forbidden = any([endpoint.startswith(name) for name
                        in constants.FORBIDDEN_ROUTE_NAMES])
    if r.match(endpoint) is not None and not is_forbidden:
        # Ensure that the name does not begin with forbidden names
        return True
    return False

def pluralize(number, singular='', plural='s'):
    """ Pluralize filter for Jinja.
    Source: http://stackoverflow.com/a/22336061/411514
    """
    if number == 1:
        return singular
    else:
        return plural

def generate_secret_key(length=31):
    """ Generates a random secret, as a string."""
    return generate_token(length=length)

def generate_number_table(num):
    """ Generate a table of number with column name pos.
    Used in models.Assignment.mysql_course_submissions_query
    """
    return ' UNION '.join('SELECT {} as pos'.format(i) for i in range(1, num + 1))
