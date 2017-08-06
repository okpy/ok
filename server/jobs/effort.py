from flask import url_for
from collections import Counter

from server import jobs
from server.models import Assignment, Score, Backup, db

@jobs.background_job
def grade_on_effort(assignment_id, full_credit, late_multiplier):
    logger = jobs.get_job_logger()

    current_user = jobs.get_current_job().user
    assignment = Assignment.query.get(assignment_id)
    submissions = assignment.course_submissions(include_empty=False)

    seen = set()
    stats = Counter()
    for i, subm in enumerate(submissions, 1):
        user_id = int(subm['user']['id'])
        if user_id in seen:
            continue

        backup = Backup.query.get(subm['backup']['id'])
        score, messages = effort_score(assignment, backup, full_credit, logger)

        if backup.submission_time > assignment.lock_date:
            messages.append('\nLate - No Credit')
            score = 0
        elif backup.submission_time > assignment.due_date:
            late_percent = 100 - round(late_multiplier * 100)
            messages.append('\nLate - {}% off'.format(late_percent))
            score = nearest_half(score * late_multiplier)

        messages.append('\nFinal Score: {}'.format(score))

        new_score = Score(score=score, kind='effort',
                message='\n'.join(messages),
                user_id=backup.submitter_id,
                assignment=assignment, backup=backup,
                grader=current_user)

        db.session.add(new_score)
        new_score.archive_duplicates()
        db.session.commit()

        if i % 100 == 0:
            logger.info('Scored {}/{}'.format(i, len(submissions)))

        if subm['group']:
            member_ids = {int(id) for id in subm['group']['group_member'].split(',')}
            seen |= member_ids
            stats[score] += len(member_ids)
        else:
            seen.add(user_id)
            stats[score] += 1

    logger.info('Scored {}/{}'.format(i, len(submissions)))
    logger.info('done!')

    logger.info('\nScore Distribution:')
    sorted_scores = sorted(stats.items(), key=lambda p: -p[0])
    for score, count in sorted_scores:
        logger.info('  {} - {}'.format(str(score).rjust(3), count))

    return url_for('admin.view_scores',
            cid=jobs.get_current_job().course_id,
            aid=assignment_id)

def nearest_half(score):
    return round(score * 2) / 2

def effort_score(assign, backup, full_credit, logger):
    """
    Gives a score based on "effort" instead of correctness.

    Effort credit for a question is given if either
        1.  The question is correct
        2.  The question has at least one testcase passed
        3.  Greater than 5 attempts were made
        4.  At least one attempt was made and the average lines added > 3
    """
    grading = backup.grading()
    analytics = backup.analytics()
    assert grading, "Grading info not found for backup: {}".format(backup.hashid)
    history = analytics and analytics.get('history') and analytics['history']['questions']

    with_effort = 0
    messages = ['Effort Breakdown']
    for question, info in grading.items():
        correct = info['locked'] == 0 and info['failed'] == 0
        showed_effort = (info['passed'] >= 1 or
                (history and history[question]['attempts'] >= 5))

        if correct or showed_effort:
            with_effort += 1

        if correct:
            message = 'Correct'
        elif showed_effort:
            message = 'Sufficient Effort'
        else:
            message = 'Not Sufficient Effort'
        messages.append('    {}: {}'.format(question, message))

    score = nearest_half(full_credit * with_effort / len(grading))
    return score, messages
