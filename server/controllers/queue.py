from flask import abort, current_app
from flask_login import current_user
import rq_dashboard

queue = rq_dashboard.blueprint

@queue.before_request
def authenticate(*args, **kwargs):
    if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()
    if not current_user.is_admin:
        abort(403)
