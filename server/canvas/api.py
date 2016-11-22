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

def canvas_api_get_list(canvas_course, endpoint, **kwargs):
    url = 'https://' + canvas_course.api_domain + '/api/v1' + endpoint
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Bearer ' + canvas_course.access_token,
    }
    params = kwargs.pop('params', {})
    params['per_page'] = 100
    response = requests.get(url, headers=headers, params=params, **kwargs)
    response.raise_for_status()
    results = response.json()
    while 'next' in response.links:
        response = requests.get(response.links['next']['url'], headers=headers)
        response.raise_for_status()
        results.extend(response.json())
    return results

def get_course(canvas_course):
    return canvas_api_request(
        canvas_course,
        'GET',
        '/courses/{}'.format(canvas_course.external_id),
    )

@cache.memoize(60)
def get_assignments(canvas_course):
    return canvas_api_get_list(
        canvas_course,
        '/courses/{}/assignments'.format(canvas_course.external_id),
    )

def get_students(canvas_course):
    # https://bcourses.berkeley.edu/doc/api/courses.html#method.courses.users
    return canvas_api_get_list(
        canvas_course,
        '/courses/{}/users'.format(canvas_course.external_id),
        params={'enrollment_type': 'student'},
    )

def score_endpoint(canvas_assignment, enrollment):
    # We can use the student ID directly here. See
    # https://bcourses.berkeley.edu/doc/api/file.object_ids.html
    return '/courses/{}/assignments/{}/submissions/sis_user_id:{}'.format(
        canvas_assignment.canvas_course.external_id,
        canvas_assignment.external_id,
        enrollment.sid,
    )

def get_score(canvas_assignment, enrollment):
    """Get a user's score (as a float) for an assignment. If the user has no
    scores, return None.
    """
    # https://bcourses.berkeley.edu/doc/api/submissions.html#method.submissions_api.show
    response = canvas_api_request(
        canvas_assignment.canvas_course,
        'GET',
        score_endpoint(canvas_assignment, enrollment),
    )
    score = response['score']
    if score is None:
        return None
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

def get_scores(canvas_assignment):
    """Get scores for an assignment. Returns a dict of
    (Canvas user ID -> float).
    """
    results = canvas_api_get_list(
        canvas_assignment.canvas_course,
        '/courses/{}/assignments/{}/submissions'.format(
            canvas_assignment.canvas_course.external_id,
            canvas_assignment.external_id,
        ),
    )
    return {score['user_id']: score['score'] for score in results}

def put_scores(canvas_assignment, grade_data):
    """Get scores for an assignment. GRADE_DATA should be a dict of
    (Canvas user ID -> float).
    """
    # https://bcourses.berkeley.edu/doc/api/submissions.html#method.submissions_api.bulk_update
    # TODO do something with returned job progress
    canvas_grade_data = {
        uid: {'posted_grade': score} for uid, score in grade_data.items()
    }
    canvas_api_request(
        canvas_assignment.canvas_course,
        'POST',
        '/courses/{}/assignments/{}/submissions/update_grades'.format(
            canvas_assignment.canvas_course.external_id,
            canvas_assignment.external_id,
        ),
        json={'grade_data': canvas_grade_data},
    )
