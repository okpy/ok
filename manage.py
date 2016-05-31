#!/usr/bin/env python3
from flask_script import Manager, Server
from flask_script.commands import ShowUrls, Clean
from flask_migrate import Migrate, MigrateCommand

from server import create_app, generate
from server.models import db, User

app = create_app('settings/dev.py')

migrate = Migrate(app, db)
manager = Manager(app)


manager.add_command("server", Server(host='0.0.0.0'))
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
    generate.seed()

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
    if app.config['ENV'] == "dev":
        db.drop_all()

@manager.command
def resetdb():
    """ Drop & create a database with all of the tables defined in
        your SQLAlchemy models.
        DO NOT USE IN PRODUCTION.
    """
    if app.config['ENV'] == "dev":
        print("Dropping database...")
        db.drop_all()
        print("Seeding database...")
        db.create_all()
        seed()


if __name__ == "__main__":
    manager.run()
