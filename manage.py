#!/usr/bin/env python

import os
from datetime import datetime, timedelta

from flask.ext.script import Manager, Server
from flask.ext.script.commands import ShowUrls, Clean
from flask.ext.migrate import Migrate, MigrateCommand
from server import create_app
from server.models import db, User, Course, Assignment, Enrollment, \
    Backup, Message, Group, Version

# default to dev config because no one should use this in
# production anyway.
env = os.environ.get('SERVER_ENV', 'dev')
app = create_app('server.settings.{0}.{1}Config'.format(env, env.capitalize()))

migrate = Migrate(app, db)
manager = Manager(app)


manager.add_command("server", Server())
manager.add_command("show-urls", ShowUrls())
manager.add_command("clean", Clean())
manager.add_command('db', MigrateCommand)


@manager.shell
def make_shell_context():
    """ Creates a python REPL with several default imports
        in the context of the app
    """
    return dict(app=app, db=db, User=User)

def make_backup(user, assign, time, messages, submit=True):
    backup = Backup(client_time=time,
                           submitter=user,
                           assignment=assign, submit=submit)
    messages = [Message(kind=k, backup=backup.id,
                contents=m) for k, m in messages.items()]
    db.session.add_all(messages)
    db.session.commit()
    backup.messages = messages
    db.session.add(backup)

@manager.command
def seed():
    """ Create default records for development.
    """
    staff_member = User(email='okstaff@okpy.org')
    db.session.add(staff_member)
    courses = [Course(offering="cal/cs61a/test16", display_name="CS61A (Test)",
                      institution="UC Berkeley"),
               Course(offering="cal/ds8/test16", display_name="DS8 (Test)",
                      institution="UC Berkeley")]
    db.session.add_all(courses)
    future = datetime.now() + timedelta(days=1)
    db.session.commit()

    # Add client version info.
    okversion = Version(name="ok", current_version="v1.5.0",
        download_link="https://github.com/Cal-CS-61A-Staff/ok-client/releases/download/v1.5.0/ok")
    db.session.add(okversion)
    okversion = Version(name="ok2", current_version="v1.5.0",
        download_link="https://github.com/Cal-CS-61A-Staff/ok-client/releases/download/v1.5.0/ok")
    db.session.add(okversion)

    students = [User(email='student{}@okpy.org'.format(i)) for i in range(60)]
    db.session.add_all(students)

    original_file = open('tests/files/before.py').read()
    modified_file = open('tests/files/after.py').read()

    files = {'difflib.py': original_file}
    assign = Assignment(name="cal/cs61a/test16/test", creator=staff_member.id,
                        course_id=courses[0].id, display_name="Test",
                        due_date=future, lock_date=future)
    db.session.add(assign)
    assign2 = Assignment(name="cal/ds8/test16/test", creator=staff_member.id,
                        course_id=courses[1].id, display_name="Test",
                        due_date=future, lock_date=future, max_group_size=2, files=files)
    db.session.add(assign2)
    db.session.commit()

    messages = {'file_contents': {'difflib.py': modified_file}, 'analytics': {}}
    for i in range(20):
        for submit in (False, True):
            time = datetime.now()-timedelta(days=i)
            make_backup(staff_member, assign2, time, messages, submit=submit)
    db.session.commit()


    staff = Enrollment(user_id=staff_member.id, course_id=courses[0].id,
                        role="staff")
    db.session.add(staff)
    staff_also_student = Enrollment(user_id=staff_member.id,
                        course_id=courses[1].id, role="student")
    db.session.add(staff_also_student)

    student_enrollment = [Enrollment(user_id=student.id, role="student",
                          course_id=courses[1].id) for student in students]
    db.session.add_all(student_enrollment)


    Group.invite(staff_member, students[0], assign2)

    db.session.commit()


@manager.command
def createdb():
    """ Creates a database with all of the tables defined in
        your SQLAlchemy models
    """
    db.create_all()

@manager.command
def dropdb():
    """ Creates a database with all of the tables defined in
        your SQLAlchemy models
    """
    if env == "dev":
        db.drop_all()

@manager.command
def resetdb():
    """ Drop & create a database with all of the tables defined in
        your SQLAlchemy models.
        DO NOT USE IN PRODUCTION.
    """
    if env == "dev":
        db.drop_all()
        print("Dropped")
        db.create_all()
        seed()


if __name__ == "__main__":
    manager.run()
