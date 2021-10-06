from server import jobs, utils
from server.constants import STAFF_ROLES
from server.models import Assignment, GradingTask, User


@jobs.background_job
def assign_grading_queues(assignment_id, staff, kind):
    logger = jobs.get_job_logger()

    cid = jobs.get_current_job().course_id

    assign = Assignment.query.filter_by(id=assignment_id, course_id=cid).one()

    selected_users = []
    for hash_id in staff:
        user = User.get_by_id(utils.decode_id(hash_id))
        if user and user.is_enrolled(cid, roles=STAFF_ROLES):
            selected_users.append(user)

    # Available backups
    data = assign.course_submissions()
    backups = set(b['backup']['id'] for b in data if b['backup'])

    tasks = GradingTask.create_staff_tasks(backups, selected_users, assignment_id, cid, kind)

    logger.log(f"{tasks} created!")
