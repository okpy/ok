from flask import Blueprint, render_template
from server.extensions import cache
from flask.ext.rq import get_queue
main = Blueprint('main', __name__)


@cache.cached(5000)
@main.route('/')
def home():
    return render_template('index.html')
