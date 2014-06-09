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
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))

    def __init__(self, email, login,
                 role, first_name, last_name):
        self.email = email
        self.login = login
        self.role = role
        self.first_name = first_name
        self.last_name = last_name

    def __repr__(self):
        return '<User %r>' % self.email

class Assignment(db.Model): #pylint: disable=R0903
    """
    The Assignment Model
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True)
    points = db.Column(db.Integer)

    def __init__(self, name, points):
        self.name = name
        self.points = points

class Submission(db.Model): #pylint: disable=R0903
    """
    The Submission Model
    """
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
    adssignment = db.relationship("Assignment",
                                  backref=db.backref('submissions', lazy='dynamic'))
    location = db.Column(db.String(255))

    def __init__(self, assignment, location):
        self.assignment = assignment
        self.location = location
