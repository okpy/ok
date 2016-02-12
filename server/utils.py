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
        raise ValueError('Could not decode hash {} into ID'.format(value))
    return numbers[0]

def local_time(dt, course):
    """Format a time string in a course's locale."""
    return course.timezone.localize(dt).strftime('%a %m/%d %H:%M %p')

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
    link = url_for('student.assignment', name=assignment.name, _external=True)
    template = 'email/invite.html'

    send_email(recipient.email, subject, text,template,
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
        html=transform(html),
        text=body)

    try:
        status, msg = sg.send(message)
        return status
    except (sendgrid.SendGridClientError, sendgrid.SendGridServerError) as e:
        log.error("Could not send email", exc_info=True)
