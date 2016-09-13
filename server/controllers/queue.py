from flask import abort, current_app, request
from flask_login import current_user, login_required
import rq_dashboard

from server import jobs

queue = rq_dashboard.blueprint

@queue.before_request
def authenticate(*args, **kwargs):
    if not current_user.is_authenticated:
        return current_app.login_manager.unauthorized()
    if not current_user.is_admin:
        abort(403)

@queue.route('/start-test-job/', methods=['POST'])
@login_required
def start_test_job():
    if current_app.config.get('ENV') == 'prod':
        abort(404)
    should_fail = bool(request.form.get('should_fail'))
    job = jobs.enqueue_job(jobs.test_job, should_fail=should_fail)
    return str(job.id)
