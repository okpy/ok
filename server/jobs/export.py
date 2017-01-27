import io
import zipfile
import json
import time

from server import jobs
from server.models import Assignment, ExternalFile
from server.utils import encode_id, local_time

@jobs.background_job
def final_export(assignment_id, user_id):
    """ Generate a zip file of all final submissions from
    enrolled students.
    Zip Strucutre: cal-cs61a../s1@a.com-s2@b.com/abc12d/hog.py

    TODO: Grab Binary Files As Well.
    """
    logger = jobs.get_job_logger()

    assignment = Assignment.query.get(assignment_id)
    requesting_user = User.query.get(user_id)

    if not assignment:
        logger.warning("No assignment found")
        raise Exception("No Assignment")
    course = assignment.course

    if not Assignment.can(assignment, requesting_user, "download"):
        raise Exception("{} does not have enough permission"
                        .format(requesting_user.email))

    logger.info('Starting...')
    enrollments = course.get_participants(['student']) # TODO: use constants

    unzip_into_folder = '{}'.format(assignment.name.replace('/', '-'))
    with io.BytesIO() as bio:
        # Get a handle to the in-memory zip in append mode
        with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED, False) as zf:
            zf.external_attr = 0o655 << 16
            # TODO: Add a password to the zip?
            seen_groups = set()
            num_students = len(enrollments)
            for index, student in enumerate(enrollments):
                stats = assignment.user_status(student.user)
                backup = stats.final_subm
                if not backup:
                    continue
                if stats.group:
                    group_emails = [m.user.email for m in stats.group.members]
                else:
                    group_emails = [student.user.email]
                group_str = '-'.join(sorted(group_emails))
                if group_str in seen_groups:
                    continue
                seen_groups.add(group_str)
                folder = "{}/{}/{}".format(unzip_into_folder, group_str, backup.hashid)

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

                percent_complete = (index+1)/num_students
                if round(percent_complete, 0) % 2 == 0:
                    logger.info(("{0:.{digits}f}% done ({} of {})"
                                 .format(percent_complete, index+1, num_students,
                                         digits=2)))

        bio.seek(0)
        upload = ExternalFile.upload(bio, user_id=user_id, course_id=course.id,
                                     name='{}_{}.zip'.format(assignment.name, time.time()),
                                     prefix='jobs/exports/{}/'.format(course.offering))

    logger.info("Saved as: {}".format(upload.object_name))
    logger.info('File ID: {0}'.format(encode_id(upload.id)))
    msg = "/files/{0}".format(encode_id(upload.id))
    return msg
