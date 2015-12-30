#!/usr/bin/env python

import os

from flask.ext.script import Manager, Server
from flask.ext.script.commands import ShowUrls, Clean
from flask.ext.migrate import Migrate, MigrateCommand
from server import create_app
from server.models import db, User

# default to dev config because no one should use this in
# production anyway.
env = os.environ.get('APPNAME_ENV', 'dev')
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
    admin = User('okadmin', 'supersafepassword')
    db.session.add(admin)
    db.session.commit()


@manager.command
def createdb():
    """ Creates a database with all of the tables defined in
        your SQLAlchemy models
    """
    db.create_all()

if __name__ == "__main__":
    manager.run()
