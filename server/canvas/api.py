import requests

from server.extensions import cache

def canvas_api_request(canvas_course, method, endpoint, **kwargs):
    url = 'https://' + canvas_course.api_domain + '/api/v1' + endpoint
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + canvas_course.access_token,
    }
    response = requests.request(method, url, headers=headers, **kwargs)
    response.raise_for_status()
    return response.json()

def score_endpoint(canvas_assignment, enrollment):
    # We can use the student ID directly here. See
    # https://bcourses.berkeley.edu/doc/api/file.object_ids.html
    return '/courses/{}/assignments/{}/submissions/sis_user_id:{}'.format(
        canvas_assignment.canvas_course.external_id,
        canvas_assignment.external_id,
        enrollment.sid,
    )

def get_course(canvas_course):
    return canvas_api_request(
        canvas_course,
        'GET',
        '/courses/{}'.format(canvas_course.external_id),
    )

@cache.memoize(60)
def get_assignments(canvas_course):
    return canvas_api_request(
        canvas_course,
        'GET',
        '/courses/{}/assignments?per_page=100'.format(canvas_course.external_id),
    )

def get_score(canvas_assignment, enrollment):
    """Get a user's score (as a float) for an assignment. If the user has no
    scores, return 0.0.
    """
    # https://bcourses.berkeley.edu/doc/api/submissions.html#method.submissions_api.show
    response = canvas_api_request(
        canvas_assignment.canvas_course,
        'GET',
        score_endpoint(canvas_assignment, enrollment),
    )
    score = response['score']
    if score is None:
        return 0.0
    else:
        return float(score)

def put_score(canvas_assignment, enrollment, score):
    """Set a user's score for an assignment."""
    # https://bcourses.berkeley.edu/doc/api/submissions.html#method.submissions_api.update
    canvas_api_request(
        canvas_assignment.canvas_course,
        'PUT',
        score_endpoint(canvas_assignment, enrollment),
        params={
            'comment[text_comment]': score.message,
            'submission[posted_grade]': score.score,
        },
    )
