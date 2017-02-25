import datetime as dt
import hashlib
import io
import json
import time
import zipfile

from server import jobs
from server.models import Assignment, ExternalFile, Group, Backup, User
from server.utils import encode_id, local_time

def student_hash(email):
    return hashlib.md5(email.strip().lower().encode()).hexdigest()

def pii_present(files, email, course, logger):
    """ Ensure the student's email is not in any of the files. """
    email = email.lower()
    for name, contents in files.items():
        if email in contents.lower() or email in name.lower():
            logger.warning("Found contact information in a submission. Ignoring".format(name))
            return True

def write_final_submission(zf, logger, assignment, student, seen, anonymize):
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

    course = assignment.course
    files = backup.files()

    if anonymize:
        for email in group_emails:
            if pii_present(files, email, assignment.course, logger):
                return
        identifier = '-'.join(sorted([student_hash(e) for e in group_emails]))
        folder = "{}/{}/".format(assignment.name.replace('/', '-'), identifier)
    else:
        folder = "{}/{}/{}".format(assignment.name.replace('/', '-'),
                                   group_str, backup.hashid)
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

    for name, contents in files.items():
        # Write the file to the in-memory zip
        zf.writestr("{}/{}".format(folder, name), contents)

def export_loop(bio, zf, logger, assignment, anonymize):
    course = assignment.course
    enrollments = course.get_students()
    seen = set()
    num_students = len(enrollments)
    for index, student in enumerate(enrollments):
        write_final_submission(zf, logger, assignment, student, seen, anonymize)
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
    Anonymized: Submission without identifying info
        Zip Strucutre: cal-cs61a../{hash}/hog.py
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
        logger.info("Starting anonymized submission export")
    else:
        logger.info("Starting final submission export")
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
                                     prefix='jobs/exports/{}/'.format(course.offering))

    logger.info("Saved as: {0}".format(upload.object_name))
    msg = "/files/{0}".format(encode_id(upload.id))
    return msg
