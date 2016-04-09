#pylint: disable=missing-docstring,invalid-name

from app import models
from app import utils
from app.constants import STUDENT_ROLE, STAFF_ROLE, VALID_ROLES

import json

SEED_OFFERING = "cal/cs61a/sp15"

def is_seeded():
    is_seed = models.Course.offering == SEED_OFFERING
    return bool(models.Course.query(is_seed).get())

def seed():
    import os
    import datetime
    import random
    from google.appengine.ext import ndb

    admin_user = models.User(
        email=["test@example.com"],
        is_admin=True
    )
    admin_user.put()

    def make_seed_course(creator):
        return models.Course(
            display_name="CS 61A",
            institution="UC Soumya",
            offering=SEED_OFFERING,
            instructor=[creator.key])

    def make_future_assignment(course, creator, name):
        date = (datetime.datetime.now() + datetime.timedelta(days=365))
        with open('app/seed/hog_template.py') as fp:
            templates = {}
            templates['hog.py'] = fp.read()
            templates['hogq.scm'] = fp.read()

        return models.Assignment(
            name='cal/CS61A/sp15/proj1',
            display_name="Hog-"+str(name),
            points=20,
            templates=json.dumps(templates),
            creator=creator.key,
            course=course.key,
            max_group_size=4,
            due_date=date,
            lock_date=date,
            url='cs61a.org/proj/hog',
            )

    # Will reject all scheme submissions
    def make_past_assignment(course, creator, name):
        date = (datetime.datetime.now() - datetime.timedelta(days=365))
        with open('app/seed/scheme_templates/scheme.py') as sc, \
            open('app/seed/scheme_templates/scheme_reader.py') as sr, \
            open('app/seed/scheme_templates/tests.scm') as tests, \
            open('app/seed/scheme_templates/questions.scm') as quest:
            templates = {}
            templates['scheme.py'] = sc.read(),
            templates['scheme_reader.py'] = sr.read(),
            templates['tests.scm'] = tests.read(),
            templates['questsions.scm'] = quest.read(),

        return models.Assignment(
            name='cal/61A/fa14/proj4',
            points=20,
            display_name="Scheme-"+str(name),
            templates=json.dumps(templates),
            course=course.key,
            creator=creator.key,
            max_group_size=4,
            due_date=date,
            lock_date=date)

    def make_hw_assignment(course, creator, name):
        date = (datetime.datetime.now() + datetime.timedelta(days=2))
        with open('app/seed/scheme_templates/scheme.py') as sc:
            templates = {}
            templates['scheme.py'] = sc.read(),

        return models.Assignment(
            name='cal/CS61A/sp15/hw1',
            points=2,
            display_name="Homework 1-"+str(name),
            templates=json.dumps(templates),
            course=course.key,
            creator=creator.key,
            max_group_size=4,
            due_date=date,
            lock_date=date)

    def make_group(assign, members):
        return models.Group(
            member=[m.key for m in members],
            assignment=assign.key
        )

    def make_invited_group(assign, members):
        return models.Group(
            member=[members[0].key],
            invited=[members[1].key],
            assignment=assign.key
        )

    def random_date():
        days, seconds = random.randint(0, 12), random.randint(0, 86399)
        delta = datetime.timedelta(days=days, seconds=seconds)
        sdate = (datetime.datetime.now() - delta)

    def make_seed_backup(assignment, submitter, final=False):
        with open('app/seed/hog_modified.py') as fp:
            messages = {}
            messages['file_contents'] = {
                'hog.py': fp.read(),
                'hogq.scm': 'Blank Stuff',
                'submit': final
            }


        messages = [models.Message(kind=kind, contents=contents)
                    for kind, contents in messages.items()]

        backup = models.Backup(
            messages=messages,
            assignment=assignment.key,
            submitter=submitter.key,
            client_time=random_date())

        backup.put()
        return backup

    def make_seed_submission(assignment, submitter, final=False, grader=admin_user):
        backup = make_seed_backup(assignment, submitter, final)
        autograder_output = 'Point breakdown:\n\ttestName: 1.0/1\n\ttestName: 1.0/1\n\nScore:\n\tTotal: 2.0'
        score = models.Score(
            score=10,
            tag="Total",
            message=autograder_output,
            grader=grader.key
        )
        score.put()
        return models.Submission(backup=backup.key, score=[score])


    def make_seed_scheme_submission(assignment, submitter, final=False):
        with open('app/seed/scheme.py') as sc, \
             open('app/seed/scheme_reader.py') as sr, \
             open('app/seed/tests.scm') as tests, \
             open('app/seed/questions.scm') as quest:
            messages = {}
            messages['file_contents'] = {
                'scheme.py': sc.read(),
                'scheme_reader.py': sr.read(),
                'tests.scm': tests.read(),
                'questsions.scm': quest.read(),
                'submit': final
            }

        messages = [models.Message(kind=kind, contents=contents)
                    for kind, contents in messages.items()]
        backup = models.Backup(
            messages=messages,
            assignment=assignment.key,
            submitter=submitter.key,
            client_time=random_date())

        backup.put()
        return models.Submission(backup=backup.key)

    def make_version(current_version):
        return models.Version(
            name='ok',
            id='ok',
            base_url='https://github.com/Cal-CS-61A-Staff/ok-client/releases/download',
            versions=[current_version],
            current_version=current_version
        )


    def make_queue(assignment, submissions, asignee):
        queue = models.Queue(
            assignment=assignment.key,
            assigned_staff=[asignee.key],
            owner=asignee.key)
        queue = queue.put()
        for subm in submissions:
            backup = subm.backup.get()
            group = None
            if backup.submitter.get().get_group(assignment.key):
              group = backup.submitter.get().get_group(assignment.key).key
            fs = models.FinalSubmission(
                assignment=assignment.key,
                group=group,
                submission=subm.key,
                submitter=backup.submitter,
                queue=queue)
            fs.put()

    def make_final_with_group(subm, assign, submitter, group):
        fs = models.FinalSubmission(submission=subm.key,
            assignment=assign.key,
            submitter=submitter.key,
            group=group.key)
        fs.put()
        return fs

    def make_final(subm, assign, submitter):
        fs = models.FinalSubmission(submission=subm.key,
            assignment=assign.key,
            submitter=submitter.key)
        fs.put()
        return fs

    def score_seed_submission(final, score, msg, grader):
        """ Add composition score """
        score = models.Score(
            tag='composition',
            score=score,
            message=msg,
            grader=grader.key)
        score.put()

        subm = final.submission.get()
        subm.score.append(score)
        subm.put()

    # Start putting things in the DB.
    c = admin_user # bad variable name in use by many parts of this script

    course = make_seed_course(admin_user)
    course.put()



    a = models.User(
        email=["dummy@admin.com"],
    )
    a.put()
    models.Participant.add_role(a.key, course.key, STAFF_ROLE)

    students = []
    group_members = []
    staff = []

    for i in range(6):
        s = models.User(
            email=["partner" + str(i) + "@teamwork.com"],
        )
        s.put()
        models.Participant.add_role(s.key, course.key, STUDENT_ROLE)
        group_members += [s]

    for i in range(9):
        s = models.User(
            email=["student" + str(i) + "@student.com"],
        )
        s.put()
        models.Participant.add_role(s.key, course.key, STUDENT_ROLE)
        students += [s]

    for i in range(9):
        s = models.User(
            email=["grader" + str(i) + "@staff.com"],
        )
        s.put()
        models.Participant.add_role(s.key, course.key, STAFF_ROLE)
        staff += [s]

    for i in range(9):
        forgetful_s = models.User(
            email=["forget"+str(i)+"@student.com"],
        )
        forgetful_s.put()
        models.Participant.add_role(forgetful_s.key, course.key, STUDENT_ROLE)
        students += [forgetful_s]

    k = models.User(
        email=["dummy2@admin.com"],
    )
    k.put()
    models.Participant.add_role(k.key, course.key, STAFF_ROLE)

    version = make_version('v1.3.0')
    version.put()
    version = make_version('v1.3.2')
    version.put()
    version = make_version('v1.3.15')
    version.put()

    # Put a few members on staff
    course.instructor.append(c.key)
    course.put()
    course.instructor.append(a.key)
    course.put()

    # Create a few assignments
    assignments = []
    for i in range(4):
        assignments += [
            make_future_assignment(course, c, i),
            make_past_assignment(course, c, i),
            make_hw_assignment(course, c, i)
        ]

    for assign in assignments:
        assign.put()
        # Create submissions
        subms = []

        # Group submission
        team1 = group_members[0:2]
        g1 = make_group(assign, team1)
        g1.put()


        team2 = group_members[2:4]
        g2 = make_invited_group(assign, team2)
        g2.put()

        team3 = group_members[4:6]
        g3 = make_group(assign, team3)
        g3.put()


        # Have each member in the group submit one
        for member in group_members:
            subm = make_seed_submission(assign, member)
            subm.put()

        # for member in group_members:
        #     subm = make_seed_scheme_submission(assign2, member)
        #     subm.put()

        group1_subm = make_seed_submission(assign, group_members[1])
        group1_subm.put()
        # Make team 1's submission final and score it.
        final = make_final_with_group(group1_subm, assign, group_members[1], g1)
        score_seed_submission(final, 2, "Nice job, group 1!", staff[8])
        subms.append(group1_subm)

        group3_subm = make_seed_submission(assign, group_members[5])
        group3_subm.put()
        # Make team 1's submission final and score it.
        final3 = make_final_with_group(group3_subm, assign, group_members[5], g3)
        score_seed_submission(final3, 1, "Awesome job, group 3!", staff[8])
        subms.append(group3_subm)

        # Make this one be a final submission though.
        # subm = make_seed_submission(assign, group_members[1], True)
        # subm.put()
        # subms.append(subm)

        # Create some Backups
        for s in students:
            for i in range(3):
                make_seed_backup(assign, s)


        # Now create indiviual submission, TODO: Enumerate instead of indexing
        for i in range(9):
            subm = make_seed_submission(assign, students[i])
            subm.put()
            #subms.append(subm)

            subm = make_seed_submission(assign, students[i], True)
            subm.put()
            subms.append(subm)

            # Make each individual submission final and score it.
            final = make_final(subm, assign, students[i])
            # Randomly assign composition so that some are ungraded:
            if i % 3 < 2:
                score_seed_submission(final, i % 3, "Good job, student %s" % str(i), staff[i])


        # Seed a queue. This should be auto-generated.
        make_queue(assign, subms[:len(subms)//2], c)
        make_queue(assign, subms[len(subms)//2:], k)

        utils.add_to_grading_queues(assign.key)