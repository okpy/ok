from flask import Blueprint, render_template, redirect

about = Blueprint('about', __name__)

@about.route('/privacy/')
def privacy():
    return render_template('about/privacy.html')

@about.route('/documentation/')
@about.route('/docs/')
def documentation():
    return redirect('https://okpy.github.io/documentation/')

@about.route('/github/')
def github():
    return redirect('https://github.com/okpy/ok')

@about.route('/publications/')
def research():
    return render_template('about/publications.html')

