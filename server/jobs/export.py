import datetime as dt
import hashlib
import json
import time

import zipstream

from server import jobs
from server.models import Assignment, ExternalFile, Group, Backup, User
from server.utils import encode_id, local_time

def student_hash(email):
    return hashlib.md5(email.strip().lower().encode()).hexdigest()

def anonymize_backup(back, course, logger):
    user_email = User.email_by_id(back.submitter_id)
    data = {
        'submitter': student_hash(user_email),
        'messages': {m.kind: m.contents for m in back.messages},
        'created': local_time(back.created, course),
    }
    # Ensure email is not in any of the messages
    for kind, message in data['messages'].items():
        if user_email and user_email.lower() in str(message).lower():
            logger.warning("Found contact information in backup {}. Ignoring".format(back.hashid))
            return {'submitter': student_hash(user_email)}
    return data

def write_final_submission(zf, logger, assignment, student, seen):
    """ Get the final submission STUDENT and write it into the zipfile ZF. """
    student_user = student.user
    stats = assignment.user_status(student_user)
    backup = stats.final_subm
    if not backup:
        return
    if stats.group:
        group_emails = [User.email_by_id(m.user_id) for m in stats.group.members]
    else:
        group_emails = [student_user.email]
    group_str = '-'.join(sorted(group_emails))
    if group_str in seen:
        return
    seen.add(group_str)
    folder = "{}/{}/{}".format(assignment.name.replace('/', '-'),
                               group_str, backup.hashid)
    course = assignment.course
    dump_info = {
        'group': group_emails,
        'scores': [s.export for s in stats.scores],
        'submitter': User.email_by_id(backup.submitter_id),
        'subm_time_local': local_time(stats.subm_time, course)
    }
    if backup.custom_submission_time:
        dump_info['custom_time_local'] = local_time(backup.custom_submission_time,
                                                    course)

    zf.writestr("{}/info.json".format(folder), json.dumps(dump_info))
    for name, contents in backup.files().items():
        zf.writestr("{}/{}".format(folder, name), contents)


def write_anon_backups(zf, logger, assignment, student, seen):
    """ Get all backups for STUDENT and write it into the zipfile ZF. """
    if student.user.id in seen:
        return
    group_ids = assignment.active_user_ids(student.user.id)
    seen |= group_ids

    backups = (Backup.query
                     .filter(Backup.submitter_id.in_(group_ids),
                             Backup.assignment_id == assignment.id)
                     .order_by(Backup.created.desc()))

    course = assignment.course
    student_history = [anonymize_backup(b, course, logger) for b in backups]

    zf.writestr("anon-{}/{}/backups.json".format(assignment.name.replace('/', '-'),
                                                 student_hash(student.user.email)),
                json.dumps(student_history))

def export_loop(zf, logger, assignment, anonymize):
    course = assignment.course
    enrollments = course.get_students()
    seen = set()
    num_students = len(enrollments)
    for index, student in enumerate(enrollments):
        if anonymize:
            write_anon_backups(zf, logger, assignment, student, seen)
        else:
            write_final_submission(zf, logger, assignment, student, seen)

        # Rough progress report
        percent_complete = ((index+1)/num_students) * 100
        if round(percent_complete, 1) % 5 == 0:
            logger.info(("{}% complete ({} of {} students processed)"
                         .format(round(percent_complete, 1), index+1,
                                 num_students)))


@jobs.background_job
def export_assignment(assignment_id, anonymized):
    """ Generate a zip file of submissions from enrolled students.

    Final Submission: One submission per student/group
        Zip Strucutre: cal-cs61a../s1@a.com-s2@b.com/abc12d/hog.py
    Anonymized: All backups without identifying info
        Zip Strucutre: anon-cal-cs61a../{hash}/backups.json
    """
    logger = jobs.get_job_logger()

    assignment = Assignment.query.get(assignment_id)
    requesting_user = jobs.get_current_job().user

    if not assignment:
        logger.warning("No assignment found")
        raise Exception("No Assignment")

    if not Assignment.can(assignment, requesting_user, "download"):
        raise Exception("{} does not have enough permission"
                        .format(requesting_user.email))
    if anonymized:
        logger.info("Starting anonymized backup")
    else:
        logger.info("Start final submission export")
    course = assignment.course
    zf = zipstream.ZipFile()
    export_loop(zf, logger, assignment, anonymized)
    created_time = local_time(dt.datetime.now(), course, fmt='%m-%d-%I-%M-%p')
    zip_name = '{}_{}.zip'.format(assignment.name.replace('/', '-'), created_time)

    logger.info("Uploading...")
    upload = ExternalFile.upload(zf, user_id=requesting_user.id, name=zip_name,
                                    course_id=course.id,
                                    prefix='research/exports/{}/'.format(course.offering))

    logger.info("Saved as: {0}".format(upload.object_name))
    msg = "/files/{0}".format(encode_id(upload.id))
    return msg
