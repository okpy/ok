import collections
import datetime
import functools
import random
import string

import loremipsum
import names
import pytz

from server.models import (db, User, Course, Assignment, Enrollment, Group,
                           Backup, Message, Comment, Version, Score,
                           GradingTask)
from server.constants import VALID_ROLES, STUDENT_ROLE, TIMEZONE
from server.extensions import cache

original_file = open('tests/files/fizzbuzz_before.py', encoding="utf8").read()
modified_file = open('tests/files/fizzbuzz_after.py', encoding="utf8").read()

def weighted_choice(choices):
    # http://stackoverflow.com/a/3679747
    total = sum(w for c, w in choices)
    r = random.uniform(0, total)
    upto = 0
    for c, w in choices:
        if upto + w >= r:
            return c
        upto += w
    assert False, "Shouldn't get here"

def gen_bool(p=0.5):
    return random.random() < p

def gen_maybe(value, p=0.5):
    return value if gen_bool(p) else None

def gen_list(gen, n, nonempty=False):
    if nonempty:
        length = random.randrange(1, n)
    else:
        length = random.randrange(n)
    return [gen() for _ in range(length)]

def gen_unique(gen, n, attr):
    generated = collections.OrderedDict()
    while len(generated) < n:
        v = gen()
        generated[getattr(v, attr)] = v
    return generated.values()

def gen_markdown():
    def gen_text():
        def alter(w):
            if gen_bool(0.9):
                return w
            return random.choice(['`{}`', '_{}_', '*{}*']).format(w)
        return ' '.join(alter(w) for w in loremipsum.get_sentence().split())

    def gen_header():
        return '{0} {1}'.format(
            '#' * random.randrange(1, 7),
            loremipsum.get_sentence())

    def gen_code():
        return '```{0}```'.format(
            '\n'.join(gen_list(loremipsum.get_sentence, 4)))

    def gen_bullets():
        return '\n'.join('* ' + s for s in gen_list(loremipsum.get_sentence, 4))

    def gen_block():
        gen = weighted_choice([
            (gen_text, 7),
            (gen_header, 1),
            (gen_code, 1),
            (gen_bullets, 1)
        ])
        return gen()

    return '\n\n'.join(gen_list(gen_block, 4, nonempty=True))

def gen_user():
    real_name = names.get_full_name()
    first_name, last_name = real_name.lower().split(' ')
    return User(
        name=gen_maybe(real_name, 0.5),
        email='{0}{1}{2}{3}@{4}'.format(
            random.choice([first_name, first_name[0]]),
            random.choice(string.ascii_lowercase) if gen_bool() else '',
            random.choice([last_name, last_name[0]]),
            random.randrange(10) if gen_bool() else '',
            random.choice(['berkeley.edu', 'gmail.com'])),
        is_admin=gen_bool(0.05))

def gen_course():
    return Course(
        offering='{0}/{1}/{2}{3}'.format(
            'cal',
            random.choice(['cs61a', 'ds88']),
            random.choice(['sp', 'su', 'fa']),
            str(random.randrange(100)).zfill(2)),
        institution='UC Berkeley',
        display_name='{0} {1}{2}'.format(
            random.choice(['CS', 'Data Science']),
            random.randrange(100),
            random.choice(['', 'A'])),
        active=gen_bool(0.3))

def gen_assignment(course):
    if gen_bool(0.5):
        display_name = random.choice([
            'Hog', 'Hog Contest', 'Maps', 'Ants', 'Scheme'
        ])
    else:
        display_name = '{0} {1}'.format(
            random.choice(['Homework', 'Lab', 'Quiz']),
            str(random.randrange(15)).zfill(2))
    name = course.offering + '/' + display_name.lower().replace(' ', '')

    last_night = (datetime.datetime.utcnow()
                          .replace(hour=0, minute=0, second=0, microsecond=0)
                  - datetime.timedelta(seconds=1))
    last_night = (pytz.timezone("America/Los_Angeles")
                      .localize(last_night)
                      .astimezone(pytz.utc))
    due_date = last_night + datetime.timedelta(
        days=random.randrange(-100, 100))
    lock_date = due_date + random.choice([
        datetime.timedelta(minutes=15),
        datetime.timedelta(days=1)
    ])

    return Assignment(
        name=name,
        course_id=course.id,
        display_name=display_name,
        due_date=due_date,
        lock_date=lock_date,
        max_group_size=weighted_choice([(1, 20), (2, 70), (3, 10)]),
        revisions_allowed=gen_bool(0.3),
        files={'fizzbuzz.py': original_file})

def gen_enrollment(user, course):
    role = weighted_choice([
        ('student', 100),
        ('grader', 2),
        ('staff', 20),
        ('instructor', 2),
    ])
    sid = ''.join(random.choice(string.digits) for _ in range(8))
    class_account = '{0}-{1}'.format(
        course.offering.split('/')[1],
        ''.join(random.choice(string.ascii_lowercase) for _ in range(3)))
    section = random.randrange(30)
    return Enrollment(
        user_id=user.id,
        course_id=course.id,
        role=role,
        sid=gen_maybe(sid, 0.4),
        class_account=gen_maybe(class_account, 0.4),
        section=gen_maybe(section, 0.4))

def gen_backup(user, assignment):
    messages = {
        'file_contents': {
            'fizzbuzz.py': modified_file,
            'moby_dick': 'Call me Ishmael.'
        },
        'analytics': {}
    }
    submit = gen_bool(0.1)
    if submit:
        messages['file_contents']['submit'] = ''
    backup = Backup(
        created=assignment.due_date -
        datetime.timedelta(seconds=random.randrange(-100000, 100)),
        submitter_id=user.id,
        assignment_id=assignment.id,
        submit=submit)
    backup.messages = [Message(kind=k, contents=m) for k, m in messages.items()]
    return backup


def gen_comment(backup):
    created = datetime.datetime.now() - datetime.timedelta(minutes=random.randrange(100))
    files = backup.files()
    filename = random.choice(list(files))
    length = len(files[filename].splitlines())
    line = random.randrange(length) + 1
    return Comment(
        created=created,
        backup_id=backup.id,
        author_id=backup.submitter.id,
        filename=filename,
        line=line,
        message=gen_markdown())

def gen_score(backup, admin, kind="autograder"):
    created = datetime.datetime.now() - datetime.timedelta(minutes=random.randrange(100))
    if kind == "composition":
        score = random.randrange(2)
    else:
        score = random.uniform(0, 100)

    return Score(
        created=created,
        backup_id=backup.id,
        assignment_id=backup.assignment.id,
        grader_id=admin.id,
        kind=kind,
        score=score,
        message=loremipsum.get_sentence())


def gen_queue(backup, grader):
    created = datetime.datetime.now() - datetime.timedelta(minutes=random.randrange(100))
    return GradingTask(
        created=created,
        backup=backup,
        assignment=backup.assignment,
        course=backup.assignment.course,
        grader=grader
    )

def gen_invite(member, invitee, assignment, accept=False):
    Group.invite(member, invitee, assignment)
    group = Group.lookup(invitee, assignment)
    if accept:
        group.accept(invitee)
    return group

def seed_users(num=25):
    print('Seeding users...')
    users = gen_unique(gen_user, num, 'email')
    db.session.add_all(users)
    db.session.commit()

def seed_courses():
    print('Seeding courses...')
    courses = gen_unique(gen_course, 4, 'offering')
    db.session.add_all(courses)
    db.session.commit()


def seed_assignments():
    print('Seeding assignments...')
    for course in Course.query.all():
        assignments = gen_unique(functools.partial(
            gen_assignment, course), 5, 'name')
        db.session.add_all(assignments)
    db.session.commit()


def seed_enrollments():
    print('Seeding enrollments...')
    for user in User.query.all():
        for course in Course.query.all():
            if not gen_bool(0.9):
                continue
            if user.is_enrolled(course.id):
                continue
            db.session.add(gen_enrollment(user, course))
    db.session.commit()


def seed_backups():
    for user in User.query.all():
        print('Seeding backups for user {0}...'.format(user.email))
        for assignment in Assignment.query.all():
            backups = gen_list(functools.partial(
                gen_backup, user, assignment), 30)
            db.session.add_all(backups)
        db.session.commit()


def seed_versions():
    print('Seeding version...')
    url = 'https://github.com/Cal-CS-61A-Staff/ok-client0/releases/download/v1.5.5/ok'
    ok = Version(name='ok-client', current_version='v1.5.5', download_link=url)
    db.session.add(ok)


def seed_comments():
    print('Seeding comments...')
    for backup in Backup.query.filter_by(submit=True).all():
        comments = gen_list(functools.partial(gen_comment, backup), 6)
        db.session.add_all(comments)
    db.session.commit()

def seed_scores():
    print('Seeding scores...')
    admin = User.query.filter_by(is_admin=True).first()
    for backup in Backup.query.filter_by(submit=True).all():
        if random.choice([True, False]):
             score = gen_score(backup, admin, kind='composition')
             db.session.add(score)
        if random.choice([True, False]):
             score = gen_score(backup, admin, kind='total')
             db.session.add(score)
    db.session.commit()

def seed_queues():
    print('Seeding queues...')
    for assign in Assignment.query.filter(Assignment.id % 2 == 0):
        graders = assign.course.get_staff()
        if not graders:
            print("No staff for ", assign.course)
            continue
        query = Backup.query.filter_by(submit=True, assignment=assign)
        for backup in query.all():
            grader = random.choice(graders)
            task = gen_queue(backup, grader.user)
            db.session.add(task)
    db.session.commit()

def seed_groups():
    print('Seeding groups...')
    for assign in Assignment.query.all():
        if assign.max_group_size < 2 or not assign.active:
            continue
        enrollments = Enrollment.query.filter_by(course=assign.course,
                                                 role=STUDENT_ROLE).all()
        students = [s.user for s in enrollments]
        while len(students) > 1:
            member, invitee = random.sample(students, 2)
            students.remove(member)
            students.remove(invitee)
            if gen_bool(0.8):  # Leave some users without any group activity
                new_group = gen_invite(member, invitee, assign,
                                       accept=gen_bool(0.8))
                db.session.add(new_group)
    db.session.commit()

def seed_flags():
    print('Seeding flags...')
    for user in User.query.all():
        seen_members = set()
        for assignment in Assignment.query.all():
            if user.id in seen_members:
                continue
            user_ids = assignment.active_user_ids(user.id)
            seen_members |= user_ids
            submissions = assignment.submissions(user_ids).all()
            if submissions and gen_bool(0.8):
                chosen = random.choice(submissions)
                assignment.flag(chosen.id, user_ids)

def seed():
    db.session.add(User(email='okstaff@okpy.org', is_admin=True))
    db.session.commit()

    random.seed(0)
    seed_users()
    seed_courses()
    seed_assignments()
    seed_enrollments()
    seed_backups()
    seed_comments()
    seed_groups()
    seed_flags()
    seed_queues()
    seed_scores()

    # Large course test. Uncomment to test large number of enrollments
    # cache.clear()
    # seed_users(num=1500)
    # seed_enrollments()
