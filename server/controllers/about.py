from flask import Blueprint, render_template, request, jsonify

about = Blueprint('about', __name__)

@about.route('/privacy')
@about.route('/tos')
def privacy():
    return render_template('about/privacy.html')
