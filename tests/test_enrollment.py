from tests import OkTestCase

from server.models import db, Enrollment, User
from server.forms import EnrollmentForm, BatchEnrollmentForm
from server.constants import STUDENT_ROLE, LAB_ASSISTANT_ROLE

class TestEnrollment(OkTestCase):

    def setUp(self):
        super().setUp()
        self.studentA = {
            'name': 'Frank Underwood',
            'email': 'frank.underwood@whitehouse.gov',
            'sid': '123456789',
            'class_account': 'cs61a-fu',
            'section': '101',
            'role': STUDENT_ROLE
        }
        self.studentB = {
            'name': 'Claire Underwood',
            'email': 'claire.underwood@whitehouse.gov',
            'sid': '987654321',
            'class_account': 'cs61a-cu',
            'section': '102',
            'role': STUDENT_ROLE
        }
        self.studentB_alt = {
            'name': 'Claire Hale Underwood',
            'email': 'claire.underwood@whitehouse.gov',
            'sid': '9876543210',
            'class_account': 'cs61a-chu',
            'section': '103',
            'role': STUDENT_ROLE
        }
        self.lab_assistantA = {
            'name': 'Ned Stark',
            'email': 'eddard.stark@winterfell.com',
            'sid': '152342343',
            'section': '101',
            'role': LAB_ASSISTANT_ROLE
        }
        self.lab_assistantB = {
            'name': 'Robb Stark',
            'email': 'robb.stark@winterfell.com',
            'sid': '189693423',
            'section': '102',
            'role': LAB_ASSISTANT_ROLE
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

        Enrollment.enroll_from_form(self.course.id, make_enrollment_form(self.lab_assistantA))
        lab_assistant = User.lookup(self.lab_assistantA['email'])
        self.lab_assistantA['id'] = lab_assistant.id

        self.enrollment_matches_info(lab_assistant, self.lab_assistantA)

    def test_unenroll(self):
        self.setup_course()

        user = User(name=self.studentA['name'], email=self.studentA['email'])
        db.session.add(user)
        db.session.commit()
        self.studentA['id'] = user.id
        
        Enrollment.create(self.course.id, [self.studentA])
        enrollment = Enrollment.query.filter_by(
            course_id=self.course.id, 
            user_id=user.id).one_or_none()
        assert enrollment is not None

        Enrollment.unenroll(enrollment)
        enrollment = Enrollment.query.filter_by(
            course_id=self.course.id, 
            user_id=user.id).one_or_none()
        assert enrollment is None

    def test_unenroll_form(self):
        self.setup_course()
        self.login(self.staff1.email)

        url = "/admin/course/{cid}/{user_id}/unenroll".format(cid=self.course.id, user_id=self.user1.id)
        response = self.client.post(url, follow_redirects=True)

        enrollment = Enrollment.query.filter_by(
            course_id=self.course.id,
            user_id=self.user1.id).one_or_none()
        assert enrollment is None
        
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
        assert enrollment.user.name == info.get('name')
        assert enrollment.user.email == info.get('email')
        assert enrollment.user_id == info.get('id')
        assert enrollment.sid == info.get('sid')
        assert enrollment.class_account == info.get('class_account')
        assert enrollment.section == info.get('section')
        assert enrollment.role == info.get('role')

    def remove_lab_assistants(self):
        [db.session.delete(e) for e in (Enrollment.query
                            .options(db.joinedload('user'))
                            .filter_by(role = LAB_ASSISTANT_ROLE,
                                    course_id = self.course.id)
                            .all()
                            )]
        db.session.commit()

    def test_lab_assistant_enroll_web(self):
        self.setup_course()
        self.remove_lab_assistants()
        self.login(self.staff1.email)
        response = self.client.get('/admin/course/{}/enrollment'.format(self.course.id))
        self.assert200(response)
        source = response.get_data().decode("utf-8")
        self.assertTrue("<span> Student </span>" in source)
        self.assertTrue("<span> Staff </span>" in source)
        self.assertFalse("<span> Lab Assistant </span>" in source)

        response = self.client.post('/admin/course/{}/enrollment'.format(self.course.id),
                        data=self.lab_assistantA, follow_redirects=True)
        self.assert200(response)
        source = response.get_data().decode("utf-8")
        self.assertTrue("<span> Student </span>" in source)
        self.assertTrue("<span> Staff </span>" in source)
        self.assertTrue("<span> Lab Assistant </span>" in source)

        response = self.client.get('/admin/course/{}/enrollment'.format(self.course.id))
        self.assert200(response)
        source = response.get_data().decode("utf-8")
        self.assertTrue("<span> Student </span>" in source)
        self.assertTrue("<span> Staff </span>" in source)
        self.assertTrue("<span> Lab Assistant </span>" in source)

        self.login(self.user1.email)
        response = self.client.post('/admin/course/{}/enrollment'.format(self.course.id),
                        data=self.lab_assistantB)
        self.assertRedirects(response, '/')

def make_enrollment_form(info):
    form = EnrollmentForm()
    form.name.data = info.get('name')
    form.email.data = info.get('email')
    form.sid.data = info.get('sid')
    form.secondary.data = info.get('class_account')
    form.section.data = info.get('section')
    form.role.data = info.get('role')
    return form
