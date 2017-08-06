from server import jobs
from server.models import Assignment, Score, db

@jobs.background_job
def grade_on_effort(assignment_id):
    logger = jobs.get_job_logger()

    logger.info('hello world!')

    # assignment = Assignment.query.get(assign_id)
    # submissions = assignment.course_submissions(include_empty=False)

    # logger.info('Students with submissions: {}'.format(len(students_with_subms)))
    # logger.info('Students without submissions: {}'.format(len(students_without_subms)))

    # query = (Score.query.options(db.joinedload('backup'))
    #               .filter_by(assignment=assignment, archived=False))

    # has_scores = defaultdict(set)

    # all_scores = query.all()
    # for score in all_scores:
    #     submitters = score.backup.enrollment_info()
    #     for s in submitters:
    #         has_scores[score.kind].add(s.user.email)

    # logger.info("---"*20)
    # for score_kind in has_scores:
    #     difference = students_with_subms.difference(has_scores[score_kind])
    #     logger.info("Number of students with {} scores is {}".format(score_kind,
    #                                                                  len(has_scores[score_kind])))
    #     logger.info("Number of students without {} scores is {}".format(score_kind,
    #                                                                     len(difference)))

    #     if difference and len(difference) < 200:
    #         logger.info("Students without {} scores: {}".format(score_kind, ', '.join(difference)))
    #     elif len(difference) >= 200:
    #         # Avoid creating very long lines.
    #         subset = list(difference)[:200]
    #         logger.info("{} students do not have {} scores. Here are a few: {}"
    #                     .format(len(difference), score_kind, ', '.join(subset)))
    #     logger.info("---"*20)