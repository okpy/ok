#!/usr/bin/env python

import os
from datetime import datetime, timedelta

from flask.ext.script import Manager, Server
from flask.ext.script.commands import ShowUrls, Clean
from flask.ext.migrate import Migrate, MigrateCommand
from server import create_app
from server.models import db, User, Course, Assignment, Participant

# default to dev config because no one should use this in
# production anyway.
env = os.environ.get('SERVER_ENV', 'dev')
app = create_app('server.settings.%sConfig' % env.capitalize())

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


@manager.command
def seed():
    """ Create default records for development.
    """
    staff_member = User('okstaff@okpy.org')
    db.session.add(staff_member)
    course = Course(offering="cs61a/sp16", display_name="CS61A (Test)")
    db.session.add(course)
    future = datetime.now() + timedelta(days=1)
    db.session.commit()

    assign = Assignment(name="cs61a/sp16/test", creator=staff_member.id,
                        course_id=course.id, display_name="test",
                        due_date=future, lock_date=future)
    db.session.add(assign)
    db.session.commit()
    staff = Participant(user=staff_member.id, course_id=course.id,
                        role="staff")
    db.session.add(staff)
    db.session.commit()


@manager.command
def createdb():
    """ Creates a database with all of the tables defined in
        your SQLAlchemy models
    """
    db.create_all()


@manager.command
def resetedb():
    """ Drop & create a database with all of the tables defined in
        your SQLAlchemy models.
        DO NOT USE IN PRODUCTION.
    """
    db.drop_all()
    db.create_all()

if __name__ == "__main__":
    manager.run()
