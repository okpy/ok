from flask import Blueprint, render_template
from server.extensions import cache

about = Blueprint('about', __name__)

@about.route('/privacy/')
def privacy():
    return render_template('about/privacy.html')
