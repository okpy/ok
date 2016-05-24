"""App constants"""

STUDENT_ROLE = 'student'
GRADER_ROLE = 'grader'
STAFF_ROLE = 'staff'
INSTRUCTOR_ROLE = 'instructor'
VALID_ROLES = [STUDENT_ROLE, GRADER_ROLE, STAFF_ROLE, INSTRUCTOR_ROLE]
STAFF_ROLES = [GRADER_ROLE, STAFF_ROLE, INSTRUCTOR_ROLE]
API_PREFIX = '/api'

GRADES_BUCKET = 'ok_grades_bucket'
TIMEZONE = 'America/Los_Angeles'

APP_URL = 'https://okpy.org/'
AUTOGRADER_URL = 'http://autograder.cs61a.org:5000'

FORBIDDEN_ROUTE_NAMES = [
    'admin',
    'api',
    'comments',
    'login',
    'logout',
    'testing-login',
]
FORBIDDEN_ASSIGNMENT_NAMES = []
