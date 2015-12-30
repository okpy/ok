from flask.ext.sqlalchemy import SQLAlchemy

from flask.ext.login import UserMixin, AnonymousUserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)
    email = db.Column(db.String(), unique=True, nullable=False)
    access_token = db.Column(db.String())
    is_admin = db.Column(db.Boolean(), default=False)
    secondary = db.Column(db.String()) # SID or Login
    #alt_email = db.Column(db.Array(db.String()))
    alt_email = db.Column(db.String())

    def __init__(self, email, access_token=None, sid=None):
        self.email = email
        self.access_token = access_token
        self.secondary = sid

    def check_login(self, value):
        return value and self.access_token == value

    def is_authenticated(self):
        if isinstance(self, AnonymousUserMixin):
            return False
        else:
            return True

    def is_active(self):
        return True

    def is_anonymous(self):
        if isinstance(self, AnonymousUserMixin):
            return True
        else:
            return False

    def get_id(self):
        return self.id

    def __repr__(self):
        return '<User %r>' % self.username


