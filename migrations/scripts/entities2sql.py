#!/usr/bin/env python2.7
"""Downloads entities from a backup location."""
import os
import sys
sys.path.append(os.environ.get('GAE_SDK'))

import contextlib
import datetime
import subprocess
import tempfile

from google.appengine.datastore import entity_pb
from google.appengine.api import datastore

def gsutil_ls(url):
    """Return a list of files in a gs:// directory."""
    output = subprocess.check_output(['gsutil', 'ls', url])
    return output.decode('utf-8').splitlines()

@contextlib.contextmanager
def gsutil_open_read(url):
    """Context manager that returns a file object that can be used to read from
    a gs:// file.
    """
    p = subprocess.Popen(['gsutil', 'cp', url, '-'], stdout=subprocess.PIPE)
    yield p.stdout
    p.stdout.close()
    p.wait()  # wait for the subprocess to exit

@contextlib.contextmanager
def gsutil_open_write(url):
    """Context manager that returns a file object that can be used to write to
    a gs:// file.
    """
    p = subprocess.Popen(['gsutil', 'cp', '-', url], stdin=subprocess.PIPE)
    yield p.stdin
    p.stdin.close()
    p.wait()  # wait for the subprocess to exit

def decode_le(s):
    n = 0
    for c in reversed(s):
        n = n * 256 + ord(c)
    return n

def read_records(f):
    # https://leveldb.googlecode.com/svn/trunk/doc/log_format.txt
    # doesn't check the crcs, but can be used in a streaming manner
    block_size = 32 << 10  # 32 KB
    record = ''
    while True:
        block = f.read(block_size)
        if not block:
            break
        while len(block) >= 7:
            size = decode_le(block[4:6])
            record_type = decode_le(block[6])
            if size == 0:
                break  # block trailer
            block = block[7:]  # chop off header
            record += block[:size]
            block = block[size:]
            if record_type == 1 or record_type == 4:
                yield record
                record = ''

def entities(kind):
    job_dirs = gsutil_ls(
        'gs://ok-migration/datastore_backup_datastore_backup_{}_{}/'
        .format(backup_date.replace('-', '_'), kind))
    job_dir = job_dirs[0]
    input_filenames = gsutil_ls(job_dir)
    for i in range(len(input_filenames)):
        input_filename = job_dir + 'output-{}'.format(i)
        print 'Reading {}'.format(input_filename)
        with gsutil_open_read(input_filename) as f:
            for record in read_records(f):
                entity_proto = entity_pb.EntityProto(contents=record)
                yield datastore.Entity.FromPb(entity_proto)

def quote(s):
    return "'{}'".format(s)

def format_value(value):
    if value is None:
        return 'NULL'
    elif isinstance(value, bool):
        return str(int(value))
    elif isinstance(value, (int, long)):
        return str(value)
    elif isinstance(value, datetime.datetime):
        return quote(value.strftime('%Y-%m-%d %H:%M:%S'))
    elif isinstance(value, (str, unicode)):
        return quote(str(value))
    else:
        raise ValueError('Cannot format value {} of type {}'.format(value, type(value).__name__))

def write_sql(row_iter, table_name):
    filename = 'gs://ok-migration/tables/{}.sql'.format(table_name)
    columns = next(row_iter)
    insert_start = 'INSERT INTO `{}` ({}) VALUES\n'.format(table_name, ', '.join(columns))
    with gsutil_open_write(filename) as f:
        current_rows = 0
        f.write('SET foreign_key_checks = 0;\n')
        f.write('TRUNCATE `{}`;\n'.format(table_name))
        f.write('SET foreign_key_checks = 1;\n')
        f.write(insert_start)
        for row in row_iter:
            if current_rows >= 1000:
                f.write(';\n')
                f.write(insert_start)
                current_rows = 0
            elif current_rows > 0:
                f.write(',')
            values = [format_value(value) for value in row]
            f.write('({})\n'.format(', '.join(values)))
            current_rows += 1
        f.write(';\n')

# Blacklisted users that will be deleted.
blacklist = (
    ['student{}@student.com'.format(n) for n in range(10)] +
    ['partner{}@teamwork.com'.format(n) for n in range(10)] +
    [
        'dummy@admin.com',
        'dummy2@admin.com',
        'test3378@example.com',
        'test33998@example.com',
        'test34998@example.com',
        'test349999@example.com',
        'test@example.com',
        'testanoetuh499912398@example.com',
        'testanoetuh49999@example.com',
    ]
)

def users():
    yield ('id', 'created', 'email', 'alt_email', 'is_admin')
    for entity in entities('Userv2'):
        user_id = entity.key().id()

        emails = entity['email']
        if len(emails) == 0:
            raise ValueError("No emails {} for user {}".format(emails, user_id))
        email = emails[0]
        alt_email = None
        if len(emails) == 2:
            alt_email = emails[1]
        elif len(emails) > 2:
            raise ValueError("Multiple emails {} for user {}".format(emails, user_id))

        if email in blacklist:
            print("Skipping blacklisted email {} for user {}".format(email, user_id))
            continue

        if email.count('@') != 1:
            print("Skipping badly formatted email {} for user {}".format(email, user_id))
            continue

        yield user_id, entity['created'], email, alt_email, entity['is_admin']

def courses():
    yield ('id', 'created', 'offering', 'institution', 'display_name', 'active', 'timezone')
    for entity in entities('Coursev2'):
        yield (
            entity.key().id(),
            entity['created'],
            entity['offering'],
            entity['institution'],
            entity['display_name'],
            entity['active'],
            'US/Pacific',
        )

def enrollments():
    yield ('id', 'created', 'user_id', 'course_id', 'role')
    for entity in entities('Participantv2'):
        if entity['user'].id() in blacklist:
            continue
        yield (
            entity.key().id(),
            entity['created'],
            entity['user'].id(),
            entity['course'].id(),
            entity['role']
        )

def assignments():
    yield ('id', 'created', 'name', 'course_id', 'display_name', 'due_date',
        'lock_date', 'creator_id', 'url', 'max_group_size', 'revisions_allowed',
        'autograding_key')
    for entity in entities('Assignmentv2'):
        due_date = entity['due_date']
        lock_date = entity.get('lock_date', None)
        if lock_date is None:
            lock_date = due_date
        yield (
            entity.key().id(),
            entity['created'],
            entity['name'],
            entity['course'].id(),
            entity['display_name'],
            due_date,
            lock_date,
            entity['creator'].id(),
            entity.get('url', None),
            entity['max_group_size'],
            entity.get('revision', False),
            entity.get('autograding_key', None),
        )

def messages():
    yield ('created', 'backup_id', 'kind', 'contents')
    for entity in entities('Backupv2'):
        if entity['submitter'].id() in blacklist:
            continue
        if 'messages.created' not in entity:
            continue
        message_data = zip(
            entity['messages.created'],
            entity['messages.kind'],
            entity['messages.contents'])
        for created, kind, contents in message_data:
            yield created, entity.key().id(), kind, contents

def backups():
    yield ('id', 'created', 'submitter_id', 'assignment_id', 'submit', 'flagged')
    for entity in entities('Backupv2'):
        if entity['submitter'].id() in blacklist:
            continue
        yield (
            entity.key().id(),
            entity['created'],
            entity['submitter'].id(),
            entity['assignment'].id(),
            False,
            False,
        )

def submissions():
    yield ('id', 'backup_id')
    for entity in entities('Submissionv2'):
        if entity['submitter'].id() in blacklist:
            continue
        yield entity.key().id(), entity['backup'].id()

def final_submissions():
    yield ('id', 'submission_id')
    for entity in entities('FinalSubmissionv2'):
        if entity['submitter'].id() in blacklist:
            continue
        yield entity.key().id(), entity['submission'].id()

def group_members():
    yield ('created', 'user_id', 'assignment_id', 'group_id', 'status')
    for entity in entities('Groupv2'):
        for user_key in entity.get('member', ()):
            if user_key.id() in blacklist:
                print 'BLACKLISTING: {}'.format(entity.key().id())
                continue
            yield (
                entity['created'],
                user_key.id(),
                entity['assignment'].id(),
                entity.key().id(),
                'active',
            )
        for user_key in entity.get('pending', ()):
            if user_key.id() in blacklist:
                print 'BLACKLISTING: {}'.format(entity.key().id())
                continue
            yield (
                entity['created'],
                user_key.id(),
                entity['assignment'].id(),
                entity.key().id(),
                'pending',
            )

def groups():
    yield ('id', 'created', 'assignment_id')
    for entity in entities('Groupv2'):
        yield entity.key().id(), entity['created'], entity['assignment'].id()

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print 'Usage: ./entities2sql.py <backup-date> <table>'
        print '  e.g. ./entities2sql.py 2016-02-11 user'
    backup_date = sys.argv[1]
    table_name = sys.argv[2]
    tables = {
        'user': users,
        'course': courses,
        'enrollment': enrollments,
        'assignment': assignments,
        'backup': backups,
        'message': messages,
        'submission': submissions,
        'final_submission': final_submissions,
        'group_member': group_members,
        'group': groups,
    }
    write_sql(tables[table_name](), table_name)
