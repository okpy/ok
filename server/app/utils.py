"""
Utility functions used by API and other services
"""

# pylint: disable=no-member

import collections
import contextlib
import logging
import datetime
import itertools
from os import path
from app import constants
import requests

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
import zipfile as zf
import csv
from flask import jsonify, request, Response, json

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import deferred
import cloudstorage as gcs

from app import app
from app.constants import GRADES_BUCKET, AUTOGRADER_URL
from app.exceptions import BadValueError

# TODO Looks like this can be removed just by relocating parse_date
# To deal with circular imports
class ModelProxy(object):
    def __getattribute__(self, key):
        import app
        return app.models.__getattribute__(key)

ModelProxy = ModelProxy()

def parse_date(date):
    # TODO Describe what date translation is happening here. Probably needs
    # a rewrite to handle daylight savings and work with other time zones.
    try:
        date = datetime.datetime.strptime(
            date, app.config["GAE_DATETIME_FORMAT"])
    except ValueError:
        date = datetime.datetime.strptime(
            date, "%Y-%m-%d %H:%M:%S")

    delta = datetime.timedelta(hours=7)
    return datetime.datetime.combine(date.date(), date.time()) + delta

def coerce_to_json(data, fields):
    """
    Coerces |data| to json, using only the allowed |fields|
    """
    if hasattr(data, 'to_json'):
        return data.to_json(fields)
    elif isinstance(data, list):
        return [mdl.to_json(fields) if hasattr(mdl, 'to_json')
                else coerce_to_json(mdl, fields) for mdl in data]
    elif isinstance(data, dict):
        if hasattr(data, 'to_json'):
            return {
                k: mdl.to_json(fields.get(k, {}))
                for k, mdl in data.iteritems()}
        else:
            return {k: coerce_to_json(mdl, fields.get(k, {}))
                    for k, mdl in data.iteritems()}
    else:
        return data

#TODO(martinis) somehow having data be an empty list doesn't make it
# return an empty list, but an empty object.
def create_api_response(status, message, data=None):
    """Creates a JSON response that contains status code (HTTP),
    an arbitrary message string, and a dictionary or list of data"""
    if isinstance(data, dict) and 'results' in data:
        data['results'] = (
            coerce_to_json(data['results'], request.fields.get('fields', {})))
    else:
        data = coerce_to_json(data, request.fields.get('fields', {}))

    if request.args.get('format', 'default') == 'raw':
        response = Response(json.dumps(data))
    else:
        response = jsonify(**{
            'status': status,
            'message': message,
            'data': data
        })
    response.status_code = status
    return response


def create_zip(file_contents={}, dir=''):
    return finish_zip(*start_zip(file_contents, dir))


def start_zip(file_contents={}, dir=''):
    """
    Creates a file from the given dictionary of filenames to contents.
    Uses specified dir to store all files.
    """
    zipfile_str = StringIO()
    zipfile = zf.ZipFile(zipfile_str, 'w')
    zipfile = add_to_zip(zipfile, file_contents, dir)
    return zipfile_str, zipfile


def finish_zip(zipfile_str, zipfile):
    zipfile.close()
    return zipfile_str.getvalue()


def add_to_zip(zipfile, files, dir=''):
    """
    Adds files to a given zip file. Uses specified dir to store files.

    :param zipfile: (ZipFile) zip archive to be extended
    :param files: (dict) map from filenames (str) to file contents.
        File contents will be encoded into a utf-8 text file.
    :param dir: (str) directory to place files in. Both this and the filename
        will be utf-8 encoded.
    """
    for filename, contents in files.items():
        zipfile.writestr(
            # TODO(knrafto) not sure if zip paths should be utf-8
            path.join(dir, filename).encode('utf-8'),
            str(contents).encode('utf-8'))
    return zipfile

def create_csv_content(content):
    """
    Return all contents in CSV file format. Content must be a list of lists.
    """
    scsv = StringIO()
    writer = csv.writer(scsv)
    try:
        writer.writerows(content)
    except csv.Error as e:
        scsv.close()
        sys.exit('Error creating CSV: {}'.format(e))
    contents = scsv.getvalue()
    scsv.close()
    return contents

def data_for_scores(assignment, user):
    """
    Returns a tuple of two values a list of lists of score info for assignment.
    Format: [['STUDENT', 'SCORE', 'MESSAGE', 'GRADER', 'TAG']]
    """
    content = [['STUDENT', 'SCORE', 'MESSAGE', 'GRADER', 'TAG']]
    course = assignment.course.get()
    groups = ModelProxy.Group.lookup_by_assignment(assignment)
    seen_members = set()

    for group in groups:
        members = group.member
        seen_members |= set(members)
        content.extend(group.scores_for_assignment(assignment))

    students = [part.user.get() for part in course.get_students(user) if part.user not in seen_members]
    for student in students:
        content.extend(student.scores_for_assignment(assignment)[0])

    return content

def create_gcs_file(gcs_filename, contents, content_type):
    """
    Creates a GCS csv file with contents CONTENTS.
    """
    try:
        gcs_file = gcs.open(gcs_filename, 'w', content_type=content_type, options={'x-goog-acl': 'project-private'})
        gcs_file.write(contents)
        gcs_file.close()
    except Exception as e:
        logging.exception("ERROR: {}".format(e))
        try:
            gcs.delete(gcs_filename)
        except gcs.NotFoundError:
            logging.info("Could not delete file " + gcs_filename)
    logging.info("Created file " + gcs_filename)


def make_csv_filename(assignment, infotype):
    """ Returns filename of format INFOTYPE_COURSE_ASSIGNMENT.csv """
    course_name = assignment.course.get().offering
    assign_name = assignment.display_name
    filename = '{}_{}_{}.csv'.format(infotype, course_name, assign_name)
    return filename.replace('/', '_').replace(' ', '_')

def paginate(entries, page, num_per_page):
    """
    Added stuff from
    https://p.ota.to/blog/2013/4/pagination-with-cursors-
        in-the-app-engine-datastore/

    Support pagination for an NDB query.
    Arguments:
      |entries| - a query which returns the items to paginate over.
      |cursor|  - a cursor of where in the pagination the user is.
      |num_per_page| - the number of results to display per page.

    The return value will be different from a regular query:
    There will be 3 things returned:
    - results: a list of results
    - forward_curs: a urlsafe hash for the cursor. Use this to get
    the next page. To retrieve the cursor object, do Cursor(urlsafe=s)
    - more: a boolean for whether or not there is more content.

    For more documentation, look at:
    https://developers.google.com/appengine/docs/python/ndb/queryclass#Query_fetch_page
    """
    if num_per_page is None:
        return {
            'results': entries.fetch(),
            'page': 1,
            'more': False
        }

    query_serialized = (
        '_'.join(str(x) for x in (
            entries.kind, entries.filters, entries.orders)))
    query_serialized = query_serialized.replace(' ', '_')
    def get_mem_key(page):
        offset = (page - 1) * num_per_page
        return "cp_%s_%s" % (query_serialized, offset)
    this_page_key = get_mem_key(page)
    next_page_key = get_mem_key(page + 1)

    cursor = None
    store_cache = True
    if page > 1:
        cursor = memcache.get(this_page_key)
        if not cursor:
            page = 1 # Reset to the front, since memcached failed
            store_cache = False

    pages_to_fetch = int(num_per_page)
    if cursor is not None:
        results, forward_cursor, more = entries.fetch_page(
            pages_to_fetch, start_cursor=cursor)
    else:
        results, forward_cursor, more = entries.fetch_page(pages_to_fetch)

    if store_cache:
        memcache.set(next_page_key, forward_cursor)

    return {
        'results': results,
        'page': page,
        'more': more
    }


def _apply_filter(query, model, arg, value, op):
    """
    Applies a filter on |model| of |arg| |op| |value| to |query|.
    """
    if '.' in arg:
        arg = arg.split('.')
    else:
        arg = [arg]

    field = model
    while arg:
        field = getattr(field, arg.pop(0), None)
        if not field:
            # Silently swallow for now
            # TODO(martinis) cause an error
            return query

    if op == "==":
        filtered = field == value
    elif op == "<":
        filtered = field < value
    elif op == "<=":
        filtered = field <= value
    elif op == ">":
        filtered = field > value
    elif op == ">=":
        filtered = field >= value
    else:
        raise ValueError("Invalid filtering operator {}".format(op))

    return query.filter(filtered)

def filter_query(query, args, model):
    """
    Applies the filters in |args| to |query|.
    |args| is a dictionary of key to value, to be used to filter the query.
    |allowed| is an optional list of the allowed filters.

    Returns a modified query with the appropriate filters.
    """
    for arg, value in args.iteritems():
        if (isinstance(value, collections.Iterable)
                and not isinstance(value, str)):
            op, value = value
        else:
            value, op = value, '=='

        query = _apply_filter(query, model, arg, value, op)

    return query


####################
# Deferred actions #
####################

ASSIGN_BATCH_SIZE = 20

# TODO: This code is used for seeding but not in the API.
def add_to_grading_queues(assign_key, cursor=None, num_updated=0):
    query = ModelProxy.FinalSubmission.query().filter(
        ModelProxy.FinalSubmission.assignment == assign_key)

    queues = list(ModelProxy.Queue.query(
        ModelProxy.Queue.assignment == assign_key))
    if not queues:
        logging.error("Tried to assign work, but no queues existed")
        return

    kwargs = {}

    if cursor:
        kwargs['start_cursor'] = cursor

    to_put = 0
    results, cursor, _ = query.fetch_page(ASSIGN_BATCH_SIZE, **kwargs)
    seen = set()
    for queue in queues:
        for subm in queue.submissions:
            if isinstance(subm, ndb.Key):
                seen.add(subm.get().submitter.id())
            else:
                seen.add(subm.submitter.id())

    for subm in results:
        user = subm.submitter.get()
        if not user.logged_in or user.key.id() in seen:
            continue
        queues.sort(key=lambda x: len(x.submissions))

        final_subm = user.get_final_submission(assign_key)
        if final_subm:
            subm = final_subm.submission.get()
            if final_subm.backup.get_messages().get('file_contents'):
                queues[0].submissions.append(subm)
                seen.add(user.key.id())
                to_put += 1

    if to_put:
        num_updated += to_put
        ndb.put_multi(queues)
        logging.debug(
            'Put %d entities to Datastore for a total of %d',
            to_put, num_updated)
        deferred.defer(
            add_to_grading_queues, assign_key, cursor=cursor,
            num_updated=num_updated)
    else:
        logging.debug(
            'add_to_grading_queues complete with %d updates!', num_updated)

def assign_staff_to_queues(assignment_key, staff_list):
        subms = ModelProxy.FinalSubmission.query(
            ModelProxy.FinalSubmission.assignment == assignment_key
        ).fetch()

        queues = []

        for instr in staff_list:
            q = ModelProxy.Queue.query(
                ModelProxy.Queue.owner == instr.key,
                ModelProxy.Queue.assignment == assignment_key).get()
            if not q:
                q = ModelProxy.Queue(
                    owner=instr.key,
                    assignment=assignment_key,
                    assigned_staff=[instr.key])
                q.put()
            queues.append(q)

        i = 0

        for subm in subms:
            subm.queue = queues[i].key
            subm.put()
            i = (i + 1) % len(staff_list)

        logging.debug(
            'assign_staff_to_queues complete with %d updates!', len(subms))

def assign_submission(backup_id, submit, revision=False):
    """
    Create Submisson and FinalSubmission records for a submitted Backup.

    :param backup_id: ID of a Backup
    :param submit: Whether this backup is a submission to be graded
    """
    backup = ModelProxy.Backup.get_by_id(backup_id)
    if not backup.get_messages().get('file_contents'):
        logging.info("Submission had no file_contents; not processing")
        return

    if submit:
        assign = backup.assignment.get_async()
        subm = ModelProxy.Submission(backup=backup.key, is_revision=revision)
        subm.put()

        # Can only make a final submission before it's due, or if it's revision
        if datetime.datetime.now() < assign.get_result().due_date:
            subm.mark_as_final()
        elif revision:
            # Mark as final handles changing revision attribute.
            subm.mark_as_final()

def sort_by_assignment(key_func, entries):
    entries = sorted(entries, key=key_func)
    return itertools.groupby(entries, key_func)

@ndb.toplevel
def merge_user(user_key, dup_user_key):
    """
    Merges |dup_user| into |user|.
    """
    if isinstance(user_key, ModelProxy.Base):
        user = user_key
        user_key = user_key.key
        get_user = lambda: user
    else:
        user = user_key.get_async()
        def get_user():
            return user.get_result()

    if isinstance(dup_user_key, ModelProxy.Base):
        dup_user = dup_user_key
        get_dup_user = lambda: dup_user
        dup_user_key = dup_user_key.key
    else:
        dup_user = dup_user_key.get_async()
        def get_dup_user():
            return dup_user.get_result()

    # Leave all groups
    G = ModelProxy.Group
    groups = G.query(ndb.OR(
        G.member == dup_user_key,
        G.invited == dup_user_key)).fetch()
    for group in groups:
        group.exit(dup_user_key)

    # Deactivate all enrollments
    E = ModelProxy.Participant
    enrolls = E.query(E.user == dup_user_key).fetch()
    for enroll in enrolls:
        # enroll.status = 'inactive'
        enroll.put_async()

    # Re-submit submissions
    S = ModelProxy.Submission
    subms = S.query(S.submitter == dup_user_key).fetch()
    for subm in subms:
        subm.resubmit(user_key)

    dup_user = get_dup_user()
    # Change email

    user = get_user()
    lowered_emails = [email.lower() for email in user.email]
    for email in dup_user.email:
        if email.lower() not in lowered_emails:
            user.email.append(email.lower())

    # Invalidate emails
    dup_user.email = ['#'+email for email in dup_user.email]
    # dup_user.status = 'inactive'
    dup_user.put_async()
    user.put_async()

    log = ModelProxy.AuditLog()
    log.event_type = "Merge user"
    log.user = user_key
    log.description = "Merged user {} with {}. Merged emails {}".format(
        dup_user_key.id(), user_key.id(), dup_user.email)
    log.obj = dup_user_key
    log.put_async()

def unique_email_address(user):
    U = ModelProxy.User

    dups = []
    for email in user.email:
        users = U.query(U.email == email).fetch()
        for found_user in users:
            if found_user.key != user.key:
                dups.append((user, found_user))

    for usera, userb in dups:
        if usera.email[0].lower() != usera.email[0]:
            user, dup_user = usera, userb
        else:
            user, dup_user = userb, usera

        merge_user(user, dup_user)

def unique_final_submission(user):
    FS = ModelProxy.FinalSubmission

    key_func = lambda subm: subm.assignment
    submissions = FS.query(FS.submitter == user.key).fetch()
    for lst in sort_by_assignment(key_func, submissions):
        if len(lst) > 1:
            lst = sorted(lst, key=lambda subm: subm.server_time)[1:]
            for subm in lst:
                subm.key.delete()

def unique_group(user):
    G = ModelProxy.Group
    key_func = lambda group: group.assignment
    groups = G.query(G.member == user.key).fetch()
    for lst in sort_by_assignment(key_func, groups):
        if len(lst) > 1:
            # TODO(martinis, denero) figure out what to do
            pass

def deferred_check_user(user_id):
    user = ModelProxy.User.get_by_id(user_id)
    if not user:
        raise deferred.PermanentTaskFailure("User id {} is invalid.".format(user_id))

    unique_email_address(user)
    unique_final_submission(user)
    unique_group(user)


def check_user(user_key):
    if isinstance(user_key, ModelProxy.User):
        user_key = user_key.key.id()

    if isinstance(user_key, ndb.Key):
        user_key = user_key.id()

    deferred.defer(deferred_check_user, user_key)


def scores_to_gcs(assignment, user):
    """ Writes all final submission scores
    for the given assignment to GCS csv file. """
    content = data_for_scores(assignment, user)
    csv_contents = create_csv_content(content)
    assign_name = assignment.name
    # Not sure what this line was doing here.
    # create_gcs_file(assignment, csv_contents, 'scores')
    csv_filename = '/{}/{}'.format(GRADES_BUCKET, make_csv_filename(assignment, 'scores'))
    create_gcs_file(csv_filename, csv_contents, 'text/csv')


def add_subm_to_zip(subm, Submission, zipfile, submission):
    """ Adds submission contents to a zipfile in-place, returns zipfile """
    try:
        if isinstance(submission, FinalSubmission):
            # Get the actual submission
            submission = submission.submission.get()
        backup = submission.backup.get()
        name, file_contents = subm.data_for_zip(backup)
        return add_to_zip(zipfile, file_contents, name)
    except BadValueError as e:
        if str(e) != 'Submission has no contents to download':
            raise e


def add_to_file_contents(file_contents, file_name, file_content):
    """ add a file to file_contents """
    file_contents[file_name] = file_content

# TODO(Alvin): generalize, cleanup everything about zip
def backup_group_file(backup, json_pretty={}):
    """ Returns group information: group_[group ID], group JSON """
    G = ModelProxy.Group
    group = G.lookup(backup.submitter, backup.assignment)
    if group:
        json_data = group.to_json()
        # use chr(97+i) to convert numbers to letters
        # 97+i converts 0, 1, 2, 3 to ascii codes corresponding to a, b, c...
        # chr converts ascii code to an ascii char
        order = {i: u['email'][0]
                 for i, u in enumerate(json_data['member'])}
        return (
            ('group_members_%s.json' % group.key.id(),
             str(json.dumps(order, **json_pretty))),
            ('group_meta_%s.json' % group.key.id(),
             str(json.dumps(json_data, **json_pretty)))
        )


def make_zip_filename(user, now):
    """ Makes zip filename: query_USER EMAIL_DATETIME.zip """
    outlawed = [' ', '.', ':', '/', '@']
    filename = '%s_%s_%s' % (
        'query',
        user.email[0],
        str(now))
    for outlaw in outlawed:
        filename = filename.replace(outlaw, '-')
    filename = '/{}/{}'.format(
        GRADES_BUCKET,
        filename)
    return filename+'.zip'


def subms_to_gcs(SearchAPI, subm, Submission, filename, data):
    """Writes all submissions for a given search query to a GCS zip file."""
    query = SearchAPI.querify(data['query'])
    gcs_file = gcs.open(filename, 'w',
        content_type='application/zip',
        options={'x-goog-acl': 'project-private'})
    with contextlib.closing(gcs_file) as f:
        with zf.ZipFile(f, 'w') as zipfile:
            for result in query:
                add_subm_to_zip(subm, Submission, zipfile, result)
    logging.info("Exported submissions to " + filename)

def submit_to_ag(assignment, messages, submitter):
    if 'file_contents' not in messages:
        return
    email = submitter.email[0]
    data = {
        'assignment': assignment.autograding_key,
        'file_contents': messages['file_contents'],
        'submitter': email
    }
    # Ensure user is enrolled.
    enrollment = ModelProxy.Participant.query(
        ModelProxy.Participant.course == assignment.course,
        ModelProxy.Participant.user == submitter.key).get()

    if not enrollment:
        raise BadValueError('User is not enrolled and cannot be autograded.')
    logging.info("Starting send to AG")
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(AUTOGRADER_URL+'/api/file/grade/continous',
        data=json.dumps(data), headers=headers)
    if r.status_code == requests.codes.ok:
        logging.info("Sent to Autograder")
        return {'status': "pending"}
    else:
        raise BadValueError('The autograder the rejected your request')

def autograde_final_subs(assignment, user, data):
    subm_ids = {}
    fsubs = list(ModelProxy.FinalSubmission.query(
                    ModelProxy.FinalSubmission.assignment == assignment.key))
    for fsub in fsubs:
      subm_ids[fsub.submission.id()] = fsub.submission.get().backup.id()

    data = {
        'subm_ids': subm_ids,
        'assignment': assignment.autograding_key,
        'access_token': data['token']
    }

    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(AUTOGRADER_URL+'/api/ok/grade/batch',
        data=json.dumps(data), headers=headers)
    if r.status_code == requests.codes.ok:
        # TODO: Contact user (via email)
      return {'status_url': AUTOGRADER_URL+'/rq', 'length': str(len(subm_ids))}
    else:
      raise BadValueError('The autograder the rejected your request')

import difflib

differ = difflib.Differ()


def diff(s1, s2):
    lines1 = s1.split('\n')
    lines2 = s2.split('\n')
    return list(differ.compare(lines1, lines2))
