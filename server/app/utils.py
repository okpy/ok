"""
Utility functions used by API and other services
"""

# pylint: disable=no-member

import collections
import logging
import datetime
import itertools

try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
import zipfile as zf
from flask import jsonify, request, Response, json

from google.appengine.api import memcache
from google.appengine.ext import ndb
from google.appengine.ext import deferred

from app import app

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

def create_zip(obj):
    """
    Creates a file from the given dictionary of filenames to contents.
    """
    zipfile_str = StringIO()
    with zf.ZipFile(zipfile_str, 'w') as zipfile:
        for filename, contents in obj.items():
            zipfile.writestr(filename, contents)
    zip_string = zipfile_str.getvalue()
    return zip_string

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
            seen.add(subm.get().submitter.id())

    for user in results:
        if not user.logged_in or user.key.id() in seen:
            continue
        queues.sort(key=lambda x: len(x.submissions))

        subm = user.get_selected_submission(assign_key, keys_only=True)
        if subm and user.is_final_submission(subm, assign_key):
            subm_got = subm.get()
            if subm_got.get_messages().get('file_contents'):
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

def assign_submission(backup_id, submit):
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
        subm = ModelProxy.Submission(backup=backup.key)
        subm.put()

        # Can only make a final submission before it's due
        if datetime.datetime.now() < assign.get_result().due_date:
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

    dup_user.email = [email + email for email in dup_user.email]
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
