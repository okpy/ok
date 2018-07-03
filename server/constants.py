"""App constants"""
import os

STUDENT_ROLE = 'student'
GRADER_ROLE = 'grader'
STAFF_ROLE = 'staff'
INSTRUCTOR_ROLE = 'instructor'
LAB_ASSISTANT_ROLE = 'lab assistant'
ROLE_DISPLAY_NAMES = {
    STUDENT_ROLE: 'Student',
    GRADER_ROLE: 'Reader',
    STAFF_ROLE: 'Teaching Assistant',
    INSTRUCTOR_ROLE: 'Instructor',
    LAB_ASSISTANT_ROLE: 'Lab Assistant',
}
VALID_ROLES = [STUDENT_ROLE, LAB_ASSISTANT_ROLE, GRADER_ROLE, STAFF_ROLE,
               INSTRUCTOR_ROLE]
STAFF_ROLES = [GRADER_ROLE, STAFF_ROLE, INSTRUCTOR_ROLE]

SCORE_KINDS = ['composition', 'correctness', 'effort', 'total', 'partner a', 'partner b',
               'regrade', 'revision', 'checkpoint 1', 'checkpoint 2',
               'private', 'autograder', 'error']

API_PREFIX = '/api'
OAUTH_SCOPES = ['all', 'email']
OAUTH_OUT_OF_BAND_URI = 'urn:ietf:wg:oauth:2.0:oob'

COMMON_LANGUAGES = ['python', 'java', 'c', 'scheme', 'lisp', 'javascript']

COURSE_ENDPOINT_FORMAT = '^\w+/\w+/(fa|sp|su|wi|au|yr)\d\d$'
ASSIGNMENT_ENDPOINT_FORMAT = COURSE_ENDPOINT_FORMAT[:-1] + '/\w+$'

GRADES_BUCKET = 'ok_grades_bucket'
TIMEZONE = 'America/Los_Angeles'
ISO_DATETIME_FMT = '%Y-%m-%d %H:%M:%S'

APPLICATION_ROOT = os.getenv('APPLICATION_ROOT', '/')

AUTOGRADER_URL = os.getenv('AUTOGRADER_URL', 'https://autograder.cs61a.org')

SENDGRID_USERNAME = os.getenv("SENDGRID_USERNAME")
SENDGRID_PASSWORD = os.getenv("SENDGRID_PASSWORD")
SENDGRID_KEY = os.getenv("SENDGRID_KEY")

FORBIDDEN_ROUTE_NAMES = [
    'about',
    'admin',
    'api',
    'comments',
    'login',
    'logout',
    'oauth',
    'rq',
    'testing-login',
]
FORBIDDEN_ASSIGNMENT_NAMES = []

# Service Providers
GOOGLE = "GOOGLE"
MICROSOFT = "MICROSOFT"

# Maximum file size to show in browser, in characters
DIFF_SIZE_LIMIT = 64 * 1024  # 64KB
SOURCE_SIZE_LIMIT = 10 * 1024 * 1024 # 10MB
MAX_UPLOAD_FILE_SIZE = 25 * 1024 * 1024 # 25MB

# Email client format for to field
EMAIL_FORMAT = "{name} <{email}>"
