import collections
import datetime
import functools
import random
import string

import names

from server.models import db, User, Course, Assignment, Enrollment, \
    Backup, Message, Group, Version

original_file = open('tests/files/fizzbuzz_before.py').read()
modified_file = open('tests/files/fizzbuzz_after.py').read()

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

def gen_list(gen, n):
    return [gen() for _ in range(n)]

def gen_unique(gen, n, attr):
    generated = collections.OrderedDict()
    while len(generated) < n:
        v = gen()
        generated[getattr(v, attr)] = v
    return generated.values()

def gen_user():
    real_name = names.get_full_name()
    first_name, last_name = real_name.lower().split(' ')
    return User(
        name=gen_maybe(real_name, 0.5),
        email='{}{}{}{}@{}'.format(
            random.choice([first_name, first_name[0]]),
            random.choice(string.ascii_lowercase) if gen_bool() else '',
            random.choice([last_name, last_name[0]]),
            random.randrange(10) if gen_bool() else '',
            random.choice(['berkeley.edu', 'gmail.com'])),
        is_admin=gen_bool(0.05))

def gen_course():
    return Course(
        offering='{}/{}/{}{}'.format(
            'cal',
            random.choice(['cs61a', 'ds88']),
            random.choice(['sp', 'su', 'fa']),
            str(random.randrange(100)).zfill(2)),
        institution='UC Berkeley',
        display_name='{} {}{}'.format(
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
        display_name = '{} {}'.format(
            random.choice(['Homework', 'Lab', 'Quiz']),
            str(random.randrange(15)).zfill(2))
    name = course.offering + '/' + display_name.lower().replace(' ', '')

    last_night = datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0) - datetime.timedelta(seconds=1)
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
        max_group_size=random.randrange(1, 3),
        revisions_allowed=gen_bool(0.3),
        files={'difflib.py': original_file})

def gen_enrollment(user, course):
    role = weighted_choice([
        ('student', 800),
        ('grader', 25),
        ('staff', 25),
        ('instructor', 2),
    ])
    sid = ''.join(random.choice(string.digits) for _ in range(8))
    class_account = '{}-{}'.format(
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
            'difflib.py': modified_file,
            'moby_dick': 'Call me Ishmael.'
        },
        'analytics': {}
    }
    backup = Backup(
        created=assignment.due_date -
            datetime.timedelta(seconds=random.randrange(-100000, 100)),
        submitter_id=user.id,
        assignment_id=assignment.id,
        submit=gen_bool(0.1))
    backup.messages = [Message(kind=k, contents=m) for k, m in messages.items()]
    return backup

def seed_users():
    print('Seeding users...')
    users = gen_unique(gen_user, 30, 'email')
    db.session.add_all(users)
    db.session.commit()

def seed_courses():
    print('Seeding courses...')
    courses = gen_unique(gen_course, 3, 'offering')
    db.session.add_all(courses)
    db.session.commit()

def seed_assignments():
    print('Seeding assignments...')
    for course in Course.query.all():
        assignments = gen_unique(functools.partial(gen_assignment, course), 5, 'name')
        db.session.add_all(assignments)
    db.session.commit()

def seed_enrollments():
    print('Seeding enrollments...')
    for user in User.query.all():
        for course in Course.query.all():
            if not gen_bool(0.9):
                continue
            db.session.add(gen_enrollment(user, course))
    db.session.commit()

def seed_backups():
    for user in User.query.all():
        print('Seeding backups for user {}...'.format(user.email))
        for assignment in Assignment.query.all():
            length = random.randrange(30)
            backups = gen_list(functools.partial(gen_backup, user, assignment), length)
            db.session.add_all(backups)
        db.session.commit()

def seed():
    random.seed(0)
    seed_users()
    seed_courses()
    seed_assignments()
    seed_enrollments()
    seed_backups()
    # TODO: groups
    # TODO: submission flagging
    # TODO: comments
    # TODO: scores
    # TODO: versions
