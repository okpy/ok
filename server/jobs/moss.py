import os
import random
import subprocess
import shlex
import glob
import shutil

from server.models import Assignment, Backup, User, Course, db
from server.utils import encode_id
from server import jobs

@jobs.background_job
def submit_to_moss(moss_id=None, assignment_id=None, language=None):
    logger = jobs.get_job_logger()
    logger.info('Starting MOSS Export...')

    assign = Assignment.query.filter_by(id=assignment_id).one_or_none()
    if not assign:
        logger.info("Could not find assignment")
        return

    subms = assign.course_submissions(include_empty=False)
    subm_keys = set(s['backup']['id'] for s in subms)

    seen = set()
    for subm in subms:
        if subm['backup']['id'] in seen:
            continue
        else:
            seen.add(subm['backup']['id'])

        if subm['group']:
            logger.info("{} -> {}".format(encode_id(subm['backup']['id']), subm['group']['group_member_emails']))
        else:
            logger.info("{} -> {}".format(encode_id(subm['backup']['id']), subm['user']['email']))

    backup_query = (Backup.query.options(db.joinedload('messages'))
                        .filter(Backup.id.in_(subm_keys))
                        .order_by(Backup.created.desc())
                        .all())

    logger.info("Retreived {} final submissions".format(len(subm_keys)))

    # TODO: Customize the location of the tmp writing (especially useful during dev)

    tmp_dir = '/tmp/moss-{}-{}'.format(assignment_id, random.randint(100, 999))

    if not os.path.exists(tmp_dir):
        os.makedirs(tmp_dir)

    # Copy in the moss script
    with open('server/jobs/moss-submission.pl', 'r') as f:
        moss_script = f.read()
        moss_script = moss_script.replace('YOUR_USER_ID_HERE', str(moss_id))
        with open(tmp_dir + "/moss.pl", 'w') as  script:
            script.write(moss_script)

    for backup in backup_query:
        # Write file into file
        file_contents = [m for m in backup.messages if m.kind == 'file_contents']
        if not file_contents:
            logger.info("{} didn't have any file contents".format(backup.hashid))
            continue
        contents = file_contents[0].contents
        dest_dir = "{}/{}/".format(tmp_dir, backup.hashid)

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        for file in contents:
            if file == 'submit':  # ignore fake file from ok-client
                continue
            with open(dest_dir + file, 'w') as f:
                f.write(contents[file])

    logger.info("Wrote all files to {}".format(tmp_dir))

    # TODO: Write template files into folder
    template_files = []

    for template in assign.files:
        dest = "{}/{}".format(tmp_dir, template)
        with open(dest, 'w') as f:
            f.write(assign.files[template])

        template_files.append(template)

    logger.info("Using template files: {}".format(' '.join(template_files)))

    # TODO: moss command
    templates = ' '.join(["-b {file}".format(file=f) for f in template_files])

    os.chdir(tmp_dir)
    files = glob.glob("*/*")

    command = "perl moss.pl -l {lang} {templates} -d {folder}".format(lang=language,
                                                                 templates=templates,
                                                                 folder=' '.join(files))

    logger.info("Running {}".format(command[:50] + ' ...'))

    try:
        process = subprocess.check_output(shlex.split(command))
        logger.info(process.decode("utf-8"))
    except subprocess.CalledProcessError as e:
        logger.warning("There was an error running your process")
        shutil.rmtree(tmp_dir)
        raise e
    finally:
        shutil.rmtree(tmp_dir)
