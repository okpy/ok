from tests import OkTestCase

from server.models import db, Enrollment, User
from server.forms import EnrollmentForm, BatchEnrollmentForm
from server.constants import STUDENT_ROLE
    
class TestEnrollment(OkTestCase):
    
    def setUp(self):
        super().setUp()
        self.studentA = {
            'name': 'Frank Underwood',
            'email': 'frank.underwood@whitehouse.gov',
            'sid': '123456789',
            'class_account': 'cs61a-fu',
            'section': '101'
        }
        self.studentB = {
            'name': 'Claire Underwood',
            'email': 'claire.underwood@whitehouse.gov',
            'sid': '987654321',
            'class_account': 'cs61a-cu',
            'section': '102'
        }
        self.studentB_alt = {
            'name': 'Claire Hale Underwood',
            'email': 'claire.underwood@whitehouse.gov',
            'sid': '9876543210',
            'class_account': 'cs61a-chu',
            'section': '103'
        }
        self.lab_assistant = {
            'name': 'Ned Stark',
            'email': 'eddard.stark@winterfell.com',
            'sid': '152342343',
            'section': '101'
        }
    
    def test_create(self):
        self.setup_course()
        
        user = User(name=self.studentA['name'], email=self.studentA['email'])
        db.session.add(user)
        db.session.commit()
        self.studentA['id'] = user.id
        
        Enrollment.create(self.course.id, [self.studentA])
        
        self.enrollment_matches_info(user, self.studentA)
        
    def test_enroll_from_form(self):
        self.setup_course()
        
        Enrollment.enroll_from_form(self.course.id, make_enrollment_form(self.studentB))
        
        user = User.lookup(self.studentB['email'])
        self.studentB['id'] = user.id
        
        self.enrollment_matches_info(user, self.studentB)

        Enrollment.enroll_from_form(self.course_id, make_enrollment_form(self.lab_assistant))

        lab_assistant = User.lookup(self.lab_assistant['email'])
        self.lab_assistant['id'] = lab_assistant.id
        
        self.enrollment_matches_info(user, self.lab_assistant)

        
    def test_enroll_from_csv(self):
        self.setup_course()
        
        template = "{email},{name},{sid},{class_account},{section}"
        form = BatchEnrollmentForm()
        form.csv.data = template.format(**self.studentA) + "\n" + template.format(**self.studentB)
        
        Enrollment.enroll_from_csv(self.course.id, form)
        
        userA = User.lookup(self.studentA['email'])
        self.studentA['id'] = userA.id
        self.enrollment_matches_info(userA, self.studentA)
        
        userB = User.lookup(self.studentB['email'])
        self.studentB['id'] = userB.id
        self.enrollment_matches_info(userB, self.studentB)
        
    def test_enroll_twice(self):
        self.setup_course()
        
        form = make_enrollment_form(self.studentB)
        Enrollment.enroll_from_form(self.course.id, form)
        
        user = User.lookup(self.studentB['email'])
        self.studentB['id'] = user.id
        
        self.enrollment_matches_info(user, self.studentB)
        
        form = make_enrollment_form(self.studentB_alt)
        Enrollment.enroll_from_form(self.course.id, form)
        
        user_updated = User.lookup(self.studentB['email'])
        self.studentB_alt['id'] = user_updated.id
        assert user.id == user_updated.id
        
        self.enrollment_matches_info(user, self.studentB_alt)
        
    def enrollment_matches_info(self, user, info):
        query = Enrollment.query.filter_by(
            user=user,
            course=self.course
        )
        assert query.count() == 1
        
        enrollment = query[0]
        assert enrollment.user.name == info['name']
        assert enrollment.user.email == info['email']
        assert enrollment.user_id == info['id']
        assert enrollment.sid == info['sid']
        assert enrollment.class_account == info['class_account']
        assert enrollment.section == info['section']
        assert enrollment.role == STUDENT_ROLE
        
        
def make_enrollment_form(info):
    form = EnrollmentForm()
    form.name.data = info['name']
    form.email.data = info['email']
    form.sid.data = info['sid']
    form.secondary.data = info['class_account']
    form.section.data = info['section']
    form.role.data = STUDENT_ROLE
    return form
    
