from collections import defaultdict

from server import jobs
from server.models import Assignment, Score, db

@jobs.background_job
def audit_missing_scores(assign_id, omit_details=('autograder', 'regrade')):
    logger = jobs.get_job_logger()

    assignment = Assignment.query.get(assign_id)
    data = assignment.course_submissions()

    students_with_subms = set(s['user']['email'] for s in data
                              if s['backup'])
    students_without_subms = set(s['user']['email'] for s in data
                                 if not s['backup'])

    logger.info('Students with submissions: {}'.format(len(students_with_subms)))
    logger.info('Students without submissions: {}'.format(len(students_without_subms)))

    query = (Score.query.options(db.joinedload('backup'))
                  .filter_by(assignment=assignment, archived=False))

    has_scores = defaultdict(set)

    all_scores = query.all()
    for score in all_scores:
        submitters = score.backup.enrollment_info()
        for s in submitters:
            has_scores[score.kind].add(s.user.email)

    logger.info("---"*20)
    for score_kind in has_scores:
        difference = students_with_subms.difference(has_scores[score_kind])
        logger.info("Number of students with {} scores is {}".format(score_kind,
                                                                     len(has_scores[score_kind])))
        logger.info("Number of students without {} scores is {}".format(score_kind,
                                                                        len(difference)))

        if difference and score_kind not in omit_details:
            logger.info("Students without {} scores: {}".format(score_kind, ', '.join(difference)))
        logger.info("---"*20)
