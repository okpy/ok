from flask import Blueprint, render_template, flash, request, redirect, \
    url_for, session,  current_app
from flask.ext.login import login_user, logout_user, login_required

from server.extensions import cache
from server.models import User, db

student = Blueprint('student', __name__)


@student.route("/")
@login_required
def index():
    return "student!", 200
