from app import models
import json

def seed():
    import os
    import datetime
    from google.appengine.ext import ndb

    def make_fake_course(creator):
        return models.Course(
            name="CS 61A",
            institution="UC Soumya",
            term="Fall",
            year="2014",
            creator=creator.key,
            staff=[])

    def make_fake_assignment(course, creator):
        with open('app/seed/hog_template.py') as fp:
            templates = {}
            templates['hog.py'] = fp.read()
        return models.Assignment(
            name='proj1',
            points=20,
            display_name="Hog",
            templates=json.dumps(templates),
            course=course.key,
            creator=creator.key,
            max_group_size=4,
            due_date=datetime.datetime.now())

    def make_fake_submission(assignment, submitter):
        with open('app/seed/hog_modified.py') as fp:
            messages = {}
            messages['file_contents'] = {
                'hog.py': fp.read()
            }
        return models.Submission(
            messages=messages,
            assignment=assignment.key,
            submitter=submitter.key)

    c = models.User(
                    key=ndb.Key("User", "dummy@admin.com"),
                    email="dummy@admin.com",
                    first_name="Admin",
                    last_name="Jones",
                    login="albert",
                    role="admin"
                )
    c.put()
    course = make_fake_course(c)
    course.put()
    assign = make_fake_assignment(course, c)
    assign.put()
    subm = make_fake_submission(assign, c)
    subm.put()

