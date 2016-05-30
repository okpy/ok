import collections
import datetime
import functools
import random
import string

import loremipsum
import names

from server.models import (db, User, Course, Assignment, Enrollment,
                           Backup, Message, Comment, Version, Score,
                           GradingTask)

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
        return '{} {}'.format(
            '#' * random.randrange(1, 7),
            loremipsum.get_sentence())

    def gen_code():
        return '```{}```'.format(
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

    last_night = datetime.datetime.utcnow().replace(
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
        files={'fizzbuzz.py': original_file})


def gen_enrollment(user, course):
    role = weighted_choice([
        ('student', 100),
        ('grader', 2),
        ('staff', 20),
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

def seed_users():
    print('Seeding users...')
    users = gen_unique(gen_user, 30, 'email')
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
            db.session.add(gen_enrollment(user, course))
    db.session.commit()


def seed_backups():
    for user in User.query.all():
        print('Seeding backups for user {}...'.format(user.email))
        for assignment in Assignment.query.all():
            backups = gen_list(functools.partial(
                gen_backup, user, assignment), 30)
            db.session.add_all(backups)
        db.session.commit()


def seed_versions():
    print('Seeding version...')
    url = 'https://github.com/Cal-CS-61A-Staff/ok-client/releases/download/v1.5.4/ok'
    ok = Version(name='ok-client', current_version='v1.5.4', download_link=url)
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
            score = gen_score(backup, admin)
            db.session.add(score)
    db.session.commit()

def seed_queues():
    print('Seeding queues...')
    for assign in Assignment.query.filter(Assignment.id % 2 == 0):
        graders = assign.course.staff()
        if not graders:
            print("No staff for ", assign.course)
            continue
        query = Backup.query.filter_by(submit=True, assignment=assign)
        for backup in query.all():
            grader = random.choice(graders)
            task = gen_queue(backup, grader)
            db.session.add(task)
    db.session.commit()

def seed():
    random.seed(0)
    seed_users()
    seed_courses()
    seed_assignments()
    seed_enrollments()
    seed_backups()
    seed_comments()
    # TODO: groups
    # TODO: submission flagging
    seed_queues()
    seed_scores()
    seed_versions()
