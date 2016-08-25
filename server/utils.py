import base64
import csv
import datetime as dt
import logging
import math
from io import StringIO
import os
import random
from urllib.parse import urlparse, urljoin

from flask import render_template, url_for
from hashids import Hashids
import humanize
from pynliner import fromString as emailFormat
import pytz
import sendgrid

from server.extensions import cache

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
    """Format a time string in a course's locale.
    Note that %-I does not perform as expected on Alpine Linux
    """
    if not time.tzinfo:
        # Assume UTC
        time = pytz.utc.localize(time)
    local = time.astimezone(pytz.timezone('America/Los_Angeles'))
    return local.strftime(fmt)

def local_time_obj(time, course):
    """Get a Datetime object in a course's locale from a TZ Aware DT object."""
    if not time.tzinfo:
        time = pytz.utc.localize(time)
    return time.astimezone(course.timezone)

def server_time_obj(time, course):
    """Convert a datetime object from a course's locale to a UTC
    datetime object.
    """
    if not time.tzinfo:
        time = course.timezone.localize(time)
    # Store using UTC on the server side.
    return time.astimezone(pytz.utc)

def natural_time(date):
    """Format a human-readable time difference (e.g. "6 days ago")"""
    if date.tzinfo:
        date = date.astimezone(pytz.utc).replace(tzinfo=None)
    now = dt.datetime.utcnow()
    return humanize.naturaltime(now - date)

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

def generate_secret_key():
    """Generates a base64-encoded secret, as a string."""
    random_bytes = bytes(random.randrange(0, 256) for _ in range(24))
    return base64.b64encode(random_bytes).decode('ascii')
