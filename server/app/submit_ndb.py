"""Implementation of submit DB calls using the Google NoSQL datastore."""

from google.appengine.ext.db import Key

from app import models

def lookup_assignments_by_name(name):
    # TODO This filter() looks wrong
    return list(models.Assignment.query().filter(models.Assignment.name == name))


def create_submission(user, assignment, contents):
    user_key = Key.from_path('User', user or 'no user')
    return models.Submission(parent=user_key, submitter=user,
                             assignment=assignment, contents=contents)
