#pylint: disable=C0103
"""
Models
"""
from flask.ext.sqlalchemy import SQLAlchemy #pylint: disable=F0401,E0611
from flask import Blueprint
from app import constants

model_blueprint = Blueprint('models', __name__)

from app import app

db = SQLAlchemy(app)

class User(db.Model): #pylint: disable=R0903
    """
    The User Model
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    login = db.Column(db.String(30))
    role = db.Column(db.Integer, default=constants.STUDENT_ROLE)

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def __repr__(self):
        return '<User %r>' % self.username

class Assignment(db.Model): #pylint: disable=R0903
    """
    The Assignment Model
    """
    id = db.Column(db.Integer, primary_key=True)
    submissions = db.relationship('Submission', backref="assignment")

    def __init__(self, *args, **kwds):
        db.Model.__init__(*args, **kwds)

class Submission(db.Model): #pylint: disable=R0903
    """
    The Submission Model
    """
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))

    def __init__(self, *args, **kwds):
        db.Model.__init__(*args, **kwds)
