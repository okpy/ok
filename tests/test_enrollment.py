from tests import OkTestCase

from server.models import db, Enrollment, User
from server.forms import EnrollmentForm, BatchEnrollmentForm
from server.constants import STUDENT_ROLE
    
STUDENT_A = {
    'name': 'Frank Underwood',
    'email': 'frank.underwood@whitehouse.gov',
    'sid': '123456789',
    'class_account': 'cs61a-fu',
    'section': '101'
}

STUDENT_B = {
    'name': 'Claire Underwood',
    'email': 'claire.underwood@whitehouse.gov',
    'sid': '987654321',
    'class_account': 'cs61a-cu',
    'section': '102'
}

class TestEnrollment(OkTestCase):
    
    def test_create(self):
        self.setup_course()
        
        info = STUDENT_A.copy()
        user = User(email=info['email'])
        db.session.add(user)
        db.session.commit()
        info['id'] = user.id
        
        Enrollment.create(self.course.id, [info])
        
        self.enrollment_matches_info(user, info)
        
    def test_enroll_from_form(self):
        self.setup_course()
        
        info = STUDENT_B.copy()
        form = EnrollmentForm()
        form.name.data = info['name']
        form.email.data = info['email']
        form.sid.data = info['sid']
        form.secondary.data = info['class_account']
        form.section.data = info['section']
        form.role.data = STUDENT_ROLE
        
        Enrollment.enroll_from_form(self.course.id, form)
        
        user = User.lookup(info['email'])
        info['id'] = user.id
        
        self.enrollment_matches_info(user, info)
        
    def test_enroll_from_csv(self):
        self.setup_course()
        
        infoA = STUDENT_A.copy()
        infoB = STUDENT_B.copy()
        template = "{email},{name},{sid},{class_account},{section}"
        form = BatchEnrollmentForm()
        form.csv.data = template.format(**infoA) + "\n" + template.format(**infoB)
        
        Enrollment.enroll_from_csv(self.course.id, form)
        
        userA = User.lookup(infoA['email'])
        infoA['id'] = userA.id
        self.enrollment_matches_info(userA, infoA)
        
        userB = User.lookup(infoB['email'])
        infoB['id'] = userB.id
        self.enrollment_matches_info(userB, infoB)
        
    def enrollment_matches_info(self, user, info):
        query = Enrollment.query.filter_by(
            user=user,
            course=self.course
        )
        assert query.count() == 1
        
        enrollment = query[0]
        assert enrollment.user_id == info['id']
        assert enrollment.sid == info['sid']
        assert enrollment.class_account == info['class_account']
        assert enrollment.section == info['section']
        assert enrollment.role == STUDENT_ROLE
        
        
