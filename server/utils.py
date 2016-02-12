import os
import logging
from urllib.parse import urlparse, urljoin

from flask import render_template, url_for
from hashids import Hashids
from premailer import transform
import sendgrid
from werkzeug.routing import BaseConverter, ValidationError

from server.extensions import cache

sg = sendgrid.SendGridClient(os.getenv('SENDGRID_API_KEY'), None, raise_errors=True)

# ID hashing configuration.
# DO NOT CHANGE ONCE THE APP IS PUBLICLY AVAILABLE. You will break every
# link with an ID in it.
hashids = Hashids(min_length=6)

def encode_id(id_number):
    return hashids.encode(id_number)

def decode_id(value):
    numbers = hashids.decode(value)
    if len(numbers) != 1:
        raise ValidationError('Could not decode hash {} into ID'.format(value))
    return numbers[0]

class BoolConverter(BaseConverter):
    def __init__(self, url_map, false_value, true_value):
        super(BoolConverter, self).__init__(url_map)
        self.false_value = false_value
        self.true_value = true_value
        self.regex = '(?:{0}|{1})'.format(false_value, true_value)

    def to_python(self, value):
        return value == self.true_value

    def to_url(self, value):
        return self.true_value if value else self.false_value

class HashidConverter(BaseConverter):
    def to_python(self, value):
        return decode_id(value)

    def to_url(self, value):
        return encode_id(value)

def is_safe_redirect_url(request, target):
  host_url = urlparse(request.host_url)
  redirect_url = urlparse(urljoin(request.host_url, target))
  return redirect_url.scheme in ('http', 'https') and \
    host_url.netloc == redirect_url.netloc

def group_action_email(members, subject, text):
    emails = [m.user.email for m in members]
    return send_email(emails, subject, text)

def invite_email(member, recipient, assignment):
    subject = "{} group invitation".format(assignment.display_name)
    text = "{} has invited you to join their group".format(member.email)
    link_text = "Respond to the invitation"
    link = url_for('student.assignment',
        course=assignment.course.offering, assign=assignment.offering_name(), _external=True)
    template = 'email/invite.html'

    send_email(recipient.email, subject, text,template,
               link_text=link_text, link=link)

def send_email(to, subject, body, template='email/notification.html',
               link_text="Sign in"):
    """ Send an email using sendgrid.
    Usage: send_email('student@okpy.org', 'Hey from OK', 'hi')
    """

    html = render_template(template, subject=subject, body=body,
       link=url_for('student.index', _external=True), link_text=link_text)

    message = sendgrid.Mail(
        to=to,
        from_name="Okpy.org",
        from_email="no-reply@okpy.org",
        subject=subject,
        html=transform(html),
        text=body)

    try:
        status, msg = sg.send(message)
        return status
    except sendgrid.SendGridClientError, sendgrid.SendGridServerError as e:
        log.error("Could not send email", exc_info=True)
