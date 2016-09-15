#!/usr/bin/env python3
import os
import binascii
import unittest

from flask_rq import get_worker
from flask_script import Manager, Server, Command
from flask_script.commands import ShowUrls, Clean

from flask_migrate import Migrate, MigrateCommand

from server import create_app, generate
from server.models import db, User, Course, Version
from server.extensions import cache

# default to dev config
env = os.environ.get('OK_ENV', 'dev')
app = create_app('settings/{0!s}.py'.format(env))

migrate = Migrate(app, db)
manager = Manager(app)

class RunTests(Command):

    def run(self):
        test_loader = unittest.defaultTestLoader
        test_runner = unittest.TextTestRunner()
        test_suite = test_loader.discover('tests/')
        test_runner.run(test_suite)

manager.add_command("server", Server(host='localhost'))
manager.add_command("show-urls", ShowUrls())
manager.add_command("clean", Clean())
manager.add_command('db', MigrateCommand)
manager.add_command('test', RunTests())

@manager.shell
def make_shell_context():
    """ Creates a python REPL with several default imports
        in the context of the app
    """
    return dict(app=app, db=db, User=User)

@manager.command
def seed():
    generate.seed()

@manager.command
def cacheflush():
    with app.app_context():
        cache.clear()
        print("Flushed")

@manager.command
def setup_default():
    admin = User(email="sumukh@berkeley.edu", is_admin=True)
    db.session.add(admin)
    admin = User(email="brian.hou@berkeley.edu", is_admin=True)
    db.session.add(admin)
    db.session.commit()
    course = Course(
            offering='cal/cs61a/sp16',
            institution='UC Berkeley',
            display_name='CS 61A',
            active=True)
    db.session.add(course)

    url = 'https://github.com/Cal-CS-61A-Staff/ok-client/releases/download/v1.5.5/ok'
    ok = Version(name='ok-client', current_version='v1.5.4', download_link=url)
    db.session.add(ok)
    db.session.commit()

@manager.command
def createdb():
    """ Creates a database with all of the tables defined in
        your SQLAlchemy models
    """
    db.create_all()
    setup_default()


@manager.command
def dropdb():
    """ Creates a database with all of the tables defined in
        your SQLAlchemy models
    """
    if app.config['ENV'] != "prod":
        db.drop_all()

@manager.command
def resetdb():
    """ Drop & create a database with all of the tables defined in
        your SQLAlchemy models.
        DO NOT USE IN PRODUCTION.
    """
    if app.config['ENV'] != "prod":
        print("Dropping database...")
        db.drop_all()
        print("Seeding database...")
        createdb()
        seed()

@manager.command
def generate_session_key():
    """ Helper for admins to generate random 24 character string. Used as the
        secret key for sessions. Must be consistent (and secret) per environment.
        Output: b'cd8c2471.................2416c0e030d09'
        Copy the value in between the quotation marks to the settings file
    """
    return binascii.hexlify(os.urandom(24))

@manager.command
def worker():
    get_worker().work()

if __name__ == "__main__":
    manager.run()
