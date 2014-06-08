from flask.ext.sqlalchemy import SQLAlchemy
from flask import Blueprint, render_template, abort
from app import constants

model_blueprint = Blueprint('models', __name__)

from app import app

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    login = db.Column(db.String(30))
    role = db.Column(db.Integer, default=constants.STUDENT_ROLE)

    def __init__(self, username, email):
        self.username = username
        self.email = email

    def __repr__(self):
        return '<User %r>' % self.username

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    submissions = db.relationship('Submission', backref="assignment")

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))
