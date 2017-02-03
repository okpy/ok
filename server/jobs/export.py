import io
import zipfile
import json
import time
import hashlib
import datetime as dt

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

def write_final_submission(bio, zf, logger, assignment, index, student, seen, percent):
    """ Get the final submission STUDENT and write it into the zipfile ZF. """
    stats = assignment.user_status(student.user)
    course = assignment.course
    backup = stats.final_subm
    if not backup:
        return
    if stats.group:
        group_emails = [m.user.email for m in stats.group.members]
    else:
        group_emails = [student.user.email]
    group_str = '-'.join(sorted(group_emails))
    if group_str in seen:
        return
    seen.add(group_str)
    folder = "{}/{}/{}".format(assignment.name.replace('/', '-'),
                               group_str, backup.hashid)

    dump_info = {
        'group': group_emails,
        'scores': [s.export for s in stats.scores],
        'submitter': backup.submitter.email,
        'subm_time_local': local_time(stats.subm_time, course)
    }
    if backup.custom_submission_time:
        dump_info['custom_time_local'] = local_time(backup.custom_submission_time,
                                                    course)

    zf.writestr("{}/info.json".format(folder), json.dumps(dump_info))
    for name, contents in backup.files().items():
        # Write the file to the in-memory zip
        zf.writestr("{}/{}".format(folder, name), contents)

    if round(percent, 0) % 5 == 0:
        logger.info(("{}% complete ({} students processed)"
                        .format(round(percent, 3), index+1)))

def write_anon_backups(bio, zf, logger, assignment, index, student, seen, percent):
    """ Get all backups for STUDENT and write it into the zipfile ZF. """
    course = assignment.course
    if student.user.id in seen:
        return
    group_ids = assignment.active_user_ids(student.user.id)
    seen |= group_ids

    backups = (Backup.query
                     .filter(Backup.submitter_id.in_(group_ids),
                             Backup.assignment_id == assignment.id)
                     .order_by(Backup.created.desc()))

    student_history = [anonymize_backup(back, course, logger) for back in backups]

    zf.writestr("anon-{}/{}/backups.json".format(assignment.name.replace('/', '-'),
                                                student_hash(student.user.email)),
                json.dumps(student_history))
    # Provide progress report
    if round(percent, 0) % 5 == 0:
        logger.info(("{}% complete ({} students processed)"
                        .format(round(percent, 3), index+1)))



def export_loop(bio, zf, logger, assignment, anonymize):
    course = assignment.course
    enrollments = course.get_participants(['student']) # TODO: use constants
    seen = set()
    num_students = len(enrollments)
    for index, student in enumerate(enrollments):
        percent_complete = ((index+1)/num_students) * 100
        if anonymize:
            write_anon_backups(bio, zf, logger, assignment, index, student, seen, percent_complete)
        else:
            write_final_submission(bio, zf, logger, assignment, index, student, seen, percent_complete)


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
    requesting_user = jobs.get_job_creator()

    if not assignment:
        logger.warning("No assignment found")
        raise Exception("No Assignment")

    if not Assignment.can(assignment, requesting_user, "download"):
        raise Exception("{} does not have enough permission"
                        .format(requesting_user.email))
    logger.info('Starting...')
    if anonymized:
        logger.info("Starting anonymized backup")
    else:
        logger.info("Start final submission export")
    course = assignment.course
    with io.BytesIO() as bio:
        # Get a handle to the in-memory zip in append mode
        with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED, False) as zf:
            zf.external_attr = 0o655 << 16
            export_loop(bio, zf, logger, assignment, anonymized)
            created_time = local_time(dt.datetime.now(), course, fmt='%m-%d-%I-%M-%p')
            zip_name = '{}_{}.zip'.format(assignment.name.replace('/', '-'), created_time)

        bio.seek(0)
        # Close zf handle to finish writing zipfile
        logger.info("Uploading...")
        upload = ExternalFile.upload(bio, user_id=requesting_user.id, name=zip_name,
                                        course_id=course.id,
                                        prefix='research/exports/{}/'.format(course.offering))

    logger.info("Saved as: {0}".format(upload.object_name))
    msg = "/files/{0}".format(encode_id(upload.id))
    return msg
