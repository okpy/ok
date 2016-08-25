"""App constants"""

STUDENT_ROLE = 'student'
GRADER_ROLE = 'grader'
STAFF_ROLE = 'staff'
INSTRUCTOR_ROLE = 'instructor'
LAB_ASSISTANT_ROLE = 'lab assistant'
VALID_ROLES = [STUDENT_ROLE, GRADER_ROLE, STAFF_ROLE, INSTRUCTOR_ROLE, LAB_ASSISTANT_ROLE]
STAFF_ROLES = [GRADER_ROLE, STAFF_ROLE, INSTRUCTOR_ROLE]
GRADE_TAGS = ['composition', 'total', 'partner a', 'partner b', 'regrade',
              'revision']
API_PREFIX = '/api'

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
