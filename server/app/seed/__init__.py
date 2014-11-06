from app import models
from app import utils

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

    def make_future_assignment(course, creator):
        date = (datetime.datetime.now() + datetime.timedelta(days=365))
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
            due_date=date)

    def make_past_assignment(course, creator):
        date = (datetime.datetime.now() - datetime.timedelta(days=365))
        with open('app/seed/hog_template.py') as fp:
            templates = {}
            templates['hog.py'] = fp.read()
        return models.Assignment(
            name='proj2',
            points=20,
            display_name="Trends",
            templates=json.dumps(templates),
            course=course.key,
            creator=creator.key,
            max_group_size=4,
            due_date=date)

    def make_group(assign, members):
        return models.Group(
            members=[m.key for m in members],
            assignment = assign.key
        )

    def make_invited_group(assign, members):
        return models.Group(
            members=[members[0].key],
            invited_members=[members[1].key],
            assignment = assign.key
        )


    def make_fake_submission(assignment, submitter):
        with open('app/seed/hog_modified.py') as fp:
            messages = {}
            messages['file_contents'] = {
                'hog.py': fp.read()
            }

        messages = [models.Message(kind=kind, contents=contents)
                    for kind, contents in messages.items()]
        return models.Submission(
            messages=messages,
            assignment=assignment.key,
            submitter=submitter.key,
            created=datetime.datetime.now())

    def make_version(current_version):
        return models.Version(
            name='ok',
            id='ok',
            base_url='https://github.com/Cal-CS-61A-Staff/ok/releases/download',
            versions=[current_version],
            current_version=current_version
        )


    def make_queue(assignment, submissions, asignee):
        queue = models.Queue(
            assignment=assignment.key,
            assigned_staff=[asignee.key])
        queue = queue.put()
        for subm in submissions:
            fs = models.FinalSubmission(
                assignment=assignment.key,
                group=subm.submitter.get().get_group(assignment.key),
                submission=subm)
            fs.put()


    # Start putting things in the DB. 
    
    c = models.User(
        key=ndb.Key("User", "test@example.com"),
        email="test@example.com",
        first_name="Admin",
        last_name="Example",
        login="Adbert",
        role="admin"
    )
    c.put()

    a = models.User(
        key=ndb.Key("User", "dummy@admin.com"),
        email="dummy@admin.com",
        first_name="Admin",
        last_name="Jones",
        login="albert",
        role="admin"
    )
    a.put()

    students = []
    group_members = []

    for i in range(4):
        s = models.User(
            key=ndb.Key("User", "partner"  + str(i) + "@teamwork.com"),
            email="partner" + str(i) + "@teamwork.com",
            first_name="partner"+ str(i),
            last_name="learning",
            login="student",
            role="student"
        )
        s.put()
        group_members += [s]


    for i in range(0,9):
        s = models.User(
            key=ndb.Key("User", "student"  + str(i) + "@student.com"),
            email="student" + str(i) + "@student.com",
            first_name="Ben"+ str(i),
            last_name="Bitdiddle",
            login="student",
            role="student"
        )
        s.put()
        students += [s]


    k = models.User(
        key=ndb.Key("User", "dummy2@admin.com"),
        email="dummy2@admin.com",
        first_name="John",
        last_name="Jones",
        login="john",
        role="admin"
    )
    k.put()

    version = make_version('v1.0.11')
    version.put()

    # Create a course
    course = make_fake_course(c)
    course.put()

    # Put a few members on staff
    course.staff.append(c.key)
    course.put()
    course.staff.append(a.key)
    course.put()


    # Create a few assignments
    assign = make_future_assignment(course, c)
    assign.put()
    assign2 = make_past_assignment(course, c)
    assign2.put()


    # Create submissions 
    subms = []

    # Group submission
    team1 = group_members[0:2]
    g1 = make_group(assign, team1)
    g1.put()

    team2 = group_members[2:4]
    g2 = make_invited_group(assign, team2)
    g2.put()

    # Have each member in the group submit one 
    for member in group_members:
        subm = make_fake_submission(assign, member)
        subm.put()
        subms.append(subm.key)

    # Now create indiviual submission
    for i in range(9):
        subm = make_fake_submission(assign, students[i])
        subm.put()
        subms.append(subm.key)



    # Seed a queue. This should be auto-generated. 
    
    q = make_queue(assign, [], c)
    q = make_queue(assign, [], k)

    # utils.assign_work(assign.key)





