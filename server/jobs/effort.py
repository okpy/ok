import math
from sqlalchemy import or_
from collections import Counter

from server import jobs
from server.models import Assignment, Score, Backup, Extension, db

@jobs.background_job
def grade_on_effort(assignment_id, full_credit, late_multiplier, required_questions, grading_url):
    logger = jobs.get_job_logger()

    current_user = jobs.get_current_job().user
    assignment = Assignment.query.get(assignment_id)
    submissions = assignment.course_submissions(include_empty=False)

    # archive all previous effort scores for this assignment
    scores = Score.query.filter(
        Score.kind == 'effort',
        Score.assignment_id == assignment_id).all()
    for score in scores:
        db.session.delete(score)

    seen = set()
    stats = Counter()
    manual = []
    for i, subm in enumerate(submissions, 1):
        user_id = int(subm['user']['id'])
        if user_id in seen:
            continue

        backup = Backup.query.get(subm['backup']['id'])
        try:
            score, messages = score_backup(backup, assignment, full_credit,
                    required_questions, late_multiplier)
        except AssertionError:
            manual.append(backup.hashid)
            continue

        member_ids = {user_id}
        if subm['group']:
            member_ids = {int(id) for id in subm['group']['group_member'].split(',')}

        for member_id in member_ids:
            new_score = Score(score=score, kind='effort',
                    message='\n'.join(messages),
                    user_id=member_id,
                    assignment=assignment, backup=backup,
                    grader=current_user)
            db.session.add(new_score)

        seen |= member_ids
        stats[score] += len(member_ids)

        if i % 100 == 0:
            logger.info('Scored {}/{}'.format(i, len(submissions)))

    logger.info('Scored {}/{}'.format(i, len(submissions)))
    logger.info('done!')

    logger.info('\nScore Distribution:')
    sorted_scores = sorted(stats.items(), key=lambda p: -p[0])
    for score, count in sorted_scores:
        logger.info('  {} - {}'.format(str(score).rjust(3), count))

    if len(manual) > 0:
        logger.info('\n{} Backups Needing Manual Grading:'.format(len(manual)))
        for backup_id in manual:
            logger.info(grading_url + backup_id)

    db.session.commit()
    return '/admin/course/{cid}/assignments/{aid}/scores'.format(
                cid=jobs.get_current_job().course_id,
                aid=assignment_id)

def score_backup(backup, assignment, full_credit, required_questions, late_multiplier):
    submission_time = get_submission_time(backup, assignment)
    if submission_time > assignment.due_date:
        submitter_id = backup.submitter_id
        backups = (
            find_ontime(submitter_id, assignment_id, assignment.due_date),
            find_ontime(submitter_id, assignment_id, assignment.lock_date),
            backup # default to the late backup
        )
        backup = best_scoring(backups, full_credit, required_questions)
        submission_time = get_submission_time(backup, assignment)
    score, messages = effort_score(backup, full_credit, required_questions)
    if submission_time > assignment.lock_date:
        messages.append('\nLate - No Credit')
        score = 0
    elif submission_time > assignment.due_date:
        late_percent = 100 - round(late_multiplier * 100)
        messages.append('\nLate - {}% off'.format(late_percent))
        score = math.floor(score * late_multiplier)
    messages.append('\nFinal Score: {}'.format(score))
    return score, messages

def get_submission_time(backup, assignment):
    """
    Returns the "time" the backup was submitted.

    If an extension exists and it hasn't expired, use its
    ``custom_submission_time`` instead of the backup's.

    If the extension's ``custom_submission_time`` is None, assume it's right
    before the assignment's due date.
    """
    extension = Extension.get_extension(backup.submitter, assignment, backup.created)
    if extension:
        return extension.custom_submission_time or assignment.due_date
    return backup.submission_time

def best_scoring(backups, full_credit, required_questions):
    def effort_grade(backup):
        score = 0
        try:
            score, _ = effort_score(backup, full_credit, required_questions)
        except AssertionError:
            pass
        return score
    non_none = (b for b in backups if b is not None)
    return max(non_none, key=effort_grade)

def find_ontime(submitter_id, assignment_id, due_date):
    submission = Backup.query.filter(
            Backup.assignment_id == assignment_id,
            Backup.submitter_id == submitter_id,
            Backup.submit == True,
            or_(Backup.created < due_date,
                Backup.custom_submission_time < due_date)
        ).order_by(Backup.created.desc()).first()
    backup = Backup.query.filter(
        Backup.assignment_id == assignment_id,
        Backup.submitter_id == submitter_id,
        or_(Backup.created < due_date,
            Backup.custom_submission_time < due_date)
    ).order_by(Backup.created.desc()).first()
    return submission or backup

def effort_score(backup, full_credit, required_questions):
    """
    Gives a score based on "effort" instead of correctness.

    Effort credit for a question is given if either
        1.  The question is correct
        2.  The question has at least one testcase passed
        3.  Greater than 3 attempts were made
    """
    grading = backup.grading()
    analytics = backup.analytics()

    with_effort = 0
    messages = ['Effort Breakdown']

    history = analytics and analytics.get('history') and analytics['history']['questions']
    questions = grading.keys()
    if history:
        questions |= history.keys()

    assert len(questions) > 0

    for question in questions:
        correct, showed_effort = False, False
        if history and history.get(question):
            info = history[question]
            correct |= info['solved']
            showed_effort |= info['attempts'] >= 3
        if grading and grading.get(question):
            info = grading[question]
            correct |= info['locked'] == 0 and info['failed'] == 0
            showed_effort |= info['passed'] >= 1

        if correct or showed_effort:
            with_effort += 1

        message = (correct and 'Correct' or
                showed_effort and 'Sufficient Effort' or
                'Not Sufficient Effort')
        messages.append('    {}: {}'.format(question, message))

    score = math.ceil(full_credit * with_effort / required_questions)
    return min(score, full_credit), messages
