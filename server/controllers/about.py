from flask import Blueprint, render_template

about = Blueprint('about', __name__)

@about.route('/privacy/')
def privacy():
    return render_template('about/privacy.html')

@about.route('/publications/')
def research():
    return render_template('about/publications.html')

