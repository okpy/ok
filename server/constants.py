"""App constants"""

STUDENT_ROLE = 'student'
GRADER_ROLE = 'grader'
STAFF_ROLE = 'staff'
INSTRUCTOR_ROLE = 'instructor'
VALID_ROLES = [STUDENT_ROLE, GRADER_ROLE, STAFF_ROLE, INSTRUCTOR_ROLE]
STAFF_ROLES = [GRADER_ROLE, STAFF_ROLE, INSTRUCTOR_ROLE]
GRADE_TAGS = ['composition', 'total', 'partner a', 'partner b', 'regrade',
              'revision']
API_PREFIX = '/api'

COURSE_ENDPOINT_FORMAT = '^\w+/\w+/\w+$'
ASSIGNMENT_ENDPOINT_FORMAT = COURSE_ENDPOINT_FORMAT[:-1] + '/\w+$'

GRADES_BUCKET = 'ok_grades_bucket'
TIMEZONE = 'America/Los_Angeles'

AUTOGRADER_URL = 'https://autograder.cs61a.org'

FORBIDDEN_ROUTE_NAMES = [
    'about',
    'admin',
    'api',
    'comments',
    'login',
    'logout',
    'testing-login',
]
FORBIDDEN_ASSIGNMENT_NAMES = []
