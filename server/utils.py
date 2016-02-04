import os
import logging

from hashids import Hashids
from werkzeug.routing import BaseConverter, ValidationError
from server.extensions import cache
from flask import render_template

import sendgrid
from premailer import transform

sg = sendgrid.SendGridClient(os.getenv('SENDGRID_API_KEY'), None, raise_errors=True)

class HashidConverter(BaseConverter):
    # ID hashing configuration.
    # DO NOT CHANGE ONCE THE APP IS PUBLICLY AVAILABLE. You will break every
    # link with an ID in it.
    hashids = Hashids(min_length=6)

    def to_python(self, value):
        numbers = self.hashids.decode(value)
        if len(numbers) != 1:
            raise ValidationError('Could not decode hash {} into ID'.format(value))
        return numbers[0]

    def to_url(self, value):
        return self.hashids.encode(value)

def send_email(to, subject, body, link="http://okpy.org", linktext="Sign into okpy.org"):
    """ Send an email using sendgrid.
    Usage: send_email('student@okpy.org', 'Hey from OK', '<h1>hi</h1>')
    """
    html = render_template('email/base.html', to=to, subject=subject,
                           body=body, link=link, link_text=linktext)
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
    except SendGridClientError as e:
        log.error(exc_info=True)
    except SendGridServerError as e:
        log.error(exc_info=True)
