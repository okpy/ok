#!/usr/bin/env python
# encoding: utf-8
#pylint: disable=no-member, no-init, too-many-public-methods
#pylint: disable=attribute-defined-outside-init
# This disable is because the tests need to be name such that
# you can understand what the test is doing from the method name.
#pylint: disable=missing-docstring
"""
tests.py

"""

import os
os.environ['FLASK_CONF'] = 'TEST'
import datetime
from test_base import APIBaseTestCase, unittest, api #pylint: disable=relative-import
from test_base import make_fake_assignment, make_fake_course #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants
from ddt import ddt, data, unpack

@ddt
class APITest(object): #pylint: disable=no-init
    """
    Simple test case for the API
    """
    @classmethod
    def get_basic_instance(cls, mutate=False):
        """
        Gets a basic instance of the model class.
        """
        raise NotImplementedError()

    def setUp(self): #pylint: disable=super-on-old-class, invalid-name
        """Set up the API Test.

        Sets up the authenticator stub, and logs you in as an admin.
        """
        super(APITest, self).setUp()
        self.login('dummy_admin')

    def get_accounts(self):
        return {
            "dummy_admin": models.User(
                email=["dummy@admin.com"],
                is_admin=True
            ),
            "dummy_staff": models.User(
                email=["brian@staff.com"],
            ),
            "dummy_student": models.User(
                email=["dummy@student.com"],
            ),
            "dummy_student2": models.User(
                email=["dummy2@student.com"],
            ),
            "dummy_student3": models.User(
                email=["dummy3@student.com"],
            ),
        }

    def enroll_accounts(self, course):
        accounts = self.get_accounts()
        add_role = models.Participant.add_role
        for instructor in course.instructor:
            add_role(instructor, course, constants.STAFF_ROLE)
        for staff in ["dummy_admin", "dummy_staff"]:
            add_role(accounts[staff], course, constants.STAFF_ROLE)
        for student in ["dummy_student", "dummy_student2", "dummy_student3"]:
            add_role(accounts[student], course, constants.STUDENT_ROLE)

    ## INDEX ##

    def test_index_empty(self):
        """Tests there are no entities when the db is created."""
        self.get_index()
        self.assertJson([])

    def test_index_one_added(self):
        """Tests that the index method gives the added entity."""
        inst = self.get_basic_instance()
        inst.put()
        self.get_index()
        self.assertJson([inst.to_json()])

    def test_index_one_removed(self):
        """Tests that removing an entity makes it disappear from the index."""
        inst = self.get_basic_instance()
        inst.put()
        self.get_index()
        self.assertJson([inst.to_json()])

        inst.key.delete()
        self.get_index()
        self.assertJson([])

    def test_index_one_removed_from_two(self):
        """
        Tests that removing one item out of two in the DB makes sure
        the other item is still found.
        """
        inst = self.get_basic_instance()
        inst.put()
        inst2 = self.get_basic_instance(mutate=True)
        inst2.put()
        self.get_index()
        self.assertTrue(inst.to_json() in self.response_json,
                        self.response_json)
        self.assertTrue(inst2.to_json() in self.response_json,
                        self.response_json)

        inst2.key.delete()
        self.get_index()
        self.assertTrue(inst.to_json() in self.response_json,
                        self.response_json)
        self.assertTrue(inst2.to_json() not in self.response_json,
                        self.response_json)

    pagination_tests = [
        (3, 2),
        (10, 3),
        (2, 3),
        (2, 2)
    ]

    @data(*pagination_tests)
    @unpack
    def test_pagination(self, total_objects, num_page):
        """
        Tests pagination by creating a specified number of entities, and
        checking if the number of entities retrieved are less than the
        specified max per page.

        total_objects - the number of entities to be created
        num_page - the maximum number of entities per page

        To create more copies of this test, just add a tuple to the
        pagination_tests list.
        @unpack allows the ddt package to work with the `pagination_tests`
        list of tuples.
        """
        for _ in range(total_objects):
            inst = self.get_basic_instance(mutate=True)
            inst.put()
        while total_objects > 0:
            if hasattr(self, 'page'):
                self.get_index(page=self.page, num_page=num_page)
            else:
                self.get_index(num_page=num_page)

            num_instances = len(self.response_json)
            if self.name == 'user' and num_instances < num_page:
                total_objects += 1 # To take care of the dummy already there

            self.assertTrue(
                num_instances <= num_page,
                "There are too many instances returned. There are " +
                str(num_instances) + " instances")
            self.assertTrue(num_instances == min(total_objects, num_page),
                "Not right number returned: " + str(total_objects) +
                " vs. " +str(num_instances) + str(self.response_json))
            total_objects -= num_page
            self.page += 1


    ## ENTITY GET ##

    def test_get_basic(self):
        """Tests that a basic get works."""
        inst = self.get_basic_instance()
        inst.put()
        self.get_entity(inst)
        self.assertJson(inst.to_json())

    def test_get_with_two_entities(self):
        """
        Tests that getting one entity with two in the DB gives the right one.
        """
        inst = self.get_basic_instance()
        inst.put()
        inst2 = self.get_basic_instance()
        inst2.put()

        self.get_entity(inst2)
        self.assertJson(inst2.to_json())

    def test_get_invalid_id_errors(self):
        """Tests that a get on an invalid ID errors."""
        self.get('/{}/1'.format(self.name))
        self.assertStatusCode(404)

    ## ENTITY POST ##

    def test_entity_create_basic(self):
        """Tests creating an empty entity."""
        inst = self.get_basic_instance(mutate=True)
        self.post_entity(inst)

        gotten = self.model.get_by_id(self.response_json['key'])
        self.assertEqual(gotten.key, inst.key)

    def test_create_two_entities(self):
        inst = self.get_basic_instance(mutate=True)
        self.post_entity(inst)
        self.assertStatusCode(201)
        gotten = self.model.get_by_id(self.response_json['key'])

        inst2 = self.get_basic_instance(mutate=True)
        self.post_entity(inst2)
        self.assertStatusCode(201)
        gotten2 = self.model.get_by_id(self.response_json['key'])

        self.assertEqual(gotten.key, inst.key)
        self.assertEqual(gotten2.key, inst2.key)

    ## ENTITY PUT ##

    ## ENTITY DELETE ##


class AssignmentAPITest(APITest, APIBaseTestCase):
    model = models.Assignment
    name = 'assignment'
    num = 1
    access_token = 'dummy_admin'

    def setUp(self):
        super(AssignmentAPITest, self).setUp()

    def get_basic_instance(self, mutate=True):
        name = 'proj'
        if mutate:
            name += str(self.num)
            self.num += 1

        self._course = make_fake_course(self.user)
        self._course.put()
        self.enroll_accounts(self._course)
        self._assignment = make_fake_assignment(self._course, self.user)
        self._assignment.name = name
        return self._assignment

    def post_entity(self, inst, *args, **kwds):
        """Posts an entity to the server."""
        data = inst
        if not isinstance(data, dict):
            data = inst.to_json()
            data['course'] = data['course']['id']

        self.post_json('/{}'.format(self.name),
                       data=data, *args, **kwds)
        if self.response_json and 'key' in self.response_json:
            if inst.key:
                self.assertEqual(inst.key.id(), self.response_json['key'])
            else:
                inst.key = models.ndb.Key(self.model,
                                          self.response_json.get('key'))

    def test_course_does_not_exist(self):
        inst = self.get_basic_instance()
        data = inst.to_json()
        data['course'] = self._course.key.id() + 100000

        self.post_entity(data)

        self.assertStatusCode(400)


class BackupAPITest(APITest, APIBaseTestCase):
    model = models.Backup
    name = 'submission'
    access_token = "submitter"

    num = 1
    def setUp(self):
        super(BackupAPITest, self).setUp()
        self.assignment_name = u'test assignment'
        self._course = make_fake_course(self.user)
        self._course.put()
        self._assign = make_fake_assignment(self._course, self.user)
        self._assign.name = self.assignment_name
        self._assign.put()

        self._submitter = self.accounts['dummy_student']
        self._submitter.put()
        self.logout()
        self.login('dummy_student')

    def get_basic_instance(self, mutate=True):
        rval = models.Backup(
            submitter=self._submitter.key,
            assignment=self._assign.key)
        return rval

    def post_entity(self, inst, *args, **kwds):
        """Posts an entity to the server."""
        data = inst.to_json()
        data['assignment'] = self.assignment_name
        data['submitter'] = data['submitter']['id']

        self.post_json('/{}'.format(self.name),
                       data=data, *args, **kwds)
        if self.response_json and 'key' in self.response_json:
            if inst.key:
                self.assertEqual(inst.key.id(), self.response_json['key'])
            else:
                inst.key = models.ndb.Key(self.model,
                                          self.response_json.get('key'))

    def test_invalid_assignment_name(self):
        self.assignment_name = 'assignment'
        inst = self.get_basic_instance()

        self.post_entity(inst)
        self.assertStatusCode(400)

    def test_sorting(self):
        time = datetime.datetime.now()
        delta = datetime.timedelta(days=1)
        changed_time = time - delta

        inst = self.get_basic_instance()
        inst.created = changed_time
        inst.put()

        inst2 = self.get_basic_instance(mutate=True)
        inst2.created = time
        inst2.put()

        self.get_index(created='>|%s' % str(changed_time - datetime.timedelta(hours=7)))
        self.assertJson([inst2.to_json()])

        self.get_index(created='<|%s' % str(time - datetime.timedelta(hours=7)))
        self.assertJson([inst.to_json()])


class CourseAPITest(APITest, APIBaseTestCase):
    model = models.Course
    name = 'course'
    num = 1
    access_token = 'dummy_admin'

    def get_basic_instance(self, mutate=True):
        name = 'testcourse'
        if mutate:
            name += str(self.num)
            self.num += 1
        rval = make_fake_course(self.user)
        rval.name = name
        return rval


class VersionAPITest(APITest, APIBaseTestCase):
    model = models.Version
    name = 'version'
    num = 1
    access_token = 'dummy_admin'

    def get_basic_instance(self, mutate=True):
        name = 'testversion'
        if mutate:
            name += str(self.num)
            self.num += 1
        return self.model(key=ndb.Key(self.model._get_kind(), name),
            name=name, versions=['1.0.0', '1.1.0'], base_url="https://www.baseurl.com")


class GroupAPITest(APITest, APIBaseTestCase):
    model = models.Group
    name = 'group'
    num = 1
    access_token = 'dummy_admin'

    def setUp(self):
        super(GroupAPITest, self).setUp()
        self.course = make_fake_course(self.user)
        self.course.put()
        self.assignment = make_fake_assignment(self.course, self.user)
        self.assignment.put()
        for student_name in [a for a in self.accounts if 'student' in a]:
            s = self.accounts[student_name]
            models.Participant.add_role(s, self.course, constants.STUDENT_ROLE)

    def get_basic_instance(self, mutate=True):
        return self.model(
            assignment=self.assignment.key,
            member=[
                self.accounts['dummy_student2'].key,
                self.accounts['dummy_student3'].key])

    def test_assignment_group(self):
        self.user = self.accounts['dummy_student2']
        inst = self.get_basic_instance()
        inst.put()

        self.get('/assignment/{}/group'.format(self.assignment.key.id()))
        self.assertEqual(self.response_json['id'], inst.key.id())

    def test_assignment_invite(self):
        self.user = self.accounts['dummy_student2']
        inst = self.get_basic_instance()
        inst.put()

        invited = self.accounts['dummy_student']
        invited.put()

        self.post_json(
            '/assignment/{}/invite'.format(self.assignment.key.id()),
            data={'email': invited.email[0]})

        self.assertEqual(inst.invited, [invited.key])

        # Check audit log
        audit_logs = models.AuditLog.query().fetch()
        self.assertEqual(len(audit_logs), 1)
        log = audit_logs[0]
        self.assertEqual(log.user, self.user.key)
        self.assertEqual('Group.invite', log.event_type)
        self.assertIn(invited.email[0], log.description)

    def test_invite(self):
        self.user = self.accounts['dummy_student2']
        inst = self.get_basic_instance()
        inst.put()
        invited = self.accounts['dummy_student']

        self.post_json(
            '/{}/{}/add_member'.format(self.name, inst.key.id()),
            data={'email': invited.email[0]})

        self.assertEqual(inst.invited, [invited.key])

    def test_accept(self):
        self.user = self.accounts['dummy_student']
        inst = self.get_basic_instance()
        inst.invited.append(self.user.key)
        inst.put()

        self.post_json('/{}/{}/accept'.format(self.name, inst.key.id()))

        self.assertEqual(inst.invited, [])
        self.assertIn(self.user.key, inst.member)

    def test_exit_invited(self):
        self.user = self.accounts['dummy_student']
        inst = self.get_basic_instance()
        inst.invited.append(self.user.key)
        inst.put()

        self.post_json('/{}/{}/decline'.format(self.name, inst.key.id()))

        self.assertEqual(inst.invited, [])
        self.assertNotIn(self.user.key, inst.member)

    def test_exit_member(self):
        self.user = self.accounts['dummy_student']
        inst = self.get_basic_instance()
        inst.member.append(self.user.key)
        inst.put()

        self.post_json(
            '/{}/{}/remove_member'.format(self.name, inst.key.id()),
                data={'email': self.user.email[0]})

        self.assertNotIn(self.user.key, inst.member)

    def test_invite_someone_in_a_group(self):
        self.user = self.accounts['dummy_student2']
        inst = self.get_basic_instance()
        inst.put()

        # Place dummy_student in another group
        invited = self.accounts['dummy_student']
        self.model(
            assignment=self.assignment.key,
            member=[invited.key, self.accounts['dummy_staff'].key]
        ).put()

        self.post_json(
            '/{}/{}/add_member'.format(self.name, inst.key.id()),
            data={'email': invited.email[0]})

        self.assertStatusCode(400)
        self.assertEqual(inst.invited, [])

    def test_remove_from_two_member_group(self):
        self.user = self.accounts['dummy_student']
        inst = self.model(assignment=self.assignment.key,
                member=[self.user.key, self.accounts['dummy_student2'].key])
        inst.put()

        self.post_json(
                '/{}/{}/remove_member'.format(self.name, inst.key.id()),
                data={'email': self.user.email[0]})

        self.assertStatusCode(200)
        self.assertEqual(inst.key.get(), None)

    def test_decline_invite_from_two_member_group(self):
        self.user = self.accounts['dummy_student']

        members = [self.accounts['dummy_student2'].key]
        inst = self.model(assignment=self.assignment.key, member=members,
                          invited=[self.user.key])
        inst.put()

        self.post_json(
               '/{}/{}/decline'.format(self.name, inst.key.id()),
               data={'email': self.user.email[0]})

        self.assertStatusCode(200)
        self.assertEqual(inst.key.get(), None)

    def test_create_two_entities(self):
        pass # No creation

    def test_entity_create_basic(self):
        pass # No creation

import operator as op


class SearchAPITest(APIBaseTestCase):
    
    API = api.SearchAPI

    def setUp(self):
        super(SearchAPITest, self).setUp()
        self.assignment_name = 'Hog Project'
        self.user = self.accounts['dummy_student2']
        self._course = make_fake_course(self.user)
        self._course.put()
        self._assign = make_fake_assignment(self._course, self.user)
        self._assign.name = self._assign.display_name = self.assignment_name
        self._assign.put()
        
    def get_accounts(self):
        return APITest().get_accounts()

    ############
    # TOKENIZE #
    ############
    
    def test_tokenize_basic(self):
        """ Tests that the single-dash is parsed normally. """
        query = '-assignment Hog'
        tokens = self.API.tokenize(query)
        self.assertTrue('assignment' in tokens[0])
        self.assertTrue('Hog' in tokens[0])
        
    def test_tokenize_operator(self):
        """ Tests that both flag and operator are parsed normally. """
        query = '-assignment --startswith Hog'
        tokens = self.API.tokenize(query)
        self.assertTrue('assignment' in tokens[0])
        self.assertTrue('Hog' in tokens[0])
        self.assertTrue('startswith' in tokens[0])

    def test_tokenize_dashes(self):
        """ Tests that dashes inside the arg are okay. """
        query = '-date --before 2015-06-22'
        tokens = self.API.tokenize(query)
        self.assertTrue('date' in tokens[0])
        self.assertTrue('before' in tokens[0])
        self.assertTrue('2015-06-22' in tokens[0])
        
    def test_tokenize_quoted_string(self):
        """ Tests that args with spaces can be grouped by quotations """
        query = '-assignment "Hog Project"'
        tokens = self.API.tokenize(query)
        self.assertTrue('assignment' in tokens[0])
        self.assertTrue('Hog Project' in tokens[0])

    def test_tokenize_single_quoted_string(self):
        """ Tests that args with spaces can be grouped by single quotations """
        query = "-assignment 'Hog Project'"
        tokens = self.API.tokenize(query)
        self.assertTrue('assignment' in tokens[0])
        self.assertTrue('Hog Project' in tokens[0])

    def test_multiple_flags(self):
        """ Tests that the multiple groups can be parsed together. """
        query = '-assignment Hog -date --before 2015-06-22'
        tokens = self.API.tokenize(query)
        self.assertTrue('assignment' in tokens[0])
        self.assertTrue('Hog' in tokens[0])
        self.assertTrue('date' in tokens[1])
        self.assertTrue('before' in tokens[1])
        self.assertTrue('2015-06-22' in tokens[1])
        
    def test_datatype_int(self):
        """ Tests that integers are parsed normally. """
        query = '-price 10'
        tokens = self.API.tokenize(query)
        self.assertTrue('price' in tokens[0])
        self.assertTrue('10' in tokens[0])
        
    def test_datatype_boolean(self):
        """ Tests that booleans are parsed normally. """
        query = '-pricey true'
        tokens = self.API.tokenize(query)
        self.assertTrue('pricey' in tokens[0])
        self.assertTrue('true' in tokens[0])

    def test_single_character_arg(self):
        """ Tests that an arg with only length one can be parsed normally. """
        query = '-price 1'
        tokens = self.API.tokenize(query)
        self.assertTrue('price' in tokens[0])
        self.assertTrue('1' in tokens[0])
        
    def test_laziness_with_quotations(self):
        """ Tests that quotations are lazily matched """
        query = '-date --before "2015-06-22" -assignment "Homework 1"'
        tokens = self.API.tokenize(query)
        self.assertTrue('date' in tokens[0])
        self.assertTrue('before' in tokens[0])
        self.assertTrue('2015-06-22' in tokens[0])
        self.assertTrue('assignment' in tokens[1])
        self.assertTrue('Homework 1' in tokens[1])
        
        
    #######################
    # TRANSLATE OPERATORS #
    #######################

    def test_translate_basic(self):
        """ Basic extraction of arg and operator """
        query = '-date --before 2015-06-22'
        scope = self.API.translate(query)
        operator, arg = scope['date']
        self.assertEqual(operator, op.__lt__)
        self.assertEqual(arg, '2015-06-22')
        
    def test_translate_operators(self):
        """ Translate to eq if no operator specified """
        query = '-assignment Scheme'
        scope = self.API.translate(query)
        operator, arg = scope['assignment']
        self.assertEqual(operator, op.__eq__)
        self.assertEqual(arg, 'Scheme')

    ###########
    # QUERIFY #
    ###########
        
    def test_flag_onlyfinal(self):
        """ Testing if onlyfinal flag operates without error """
        query = '-assignment "%s" -onlyfinal %s'
        self.API.querify(query % (self.assignment_name, 'true'))
        self.API.querify(query % (self.assignment_name, 'false'))

    def test_flag_onlyfinal_with_quotations(self):
        """ Testing if onlyfinal flag with double quotations operates without error """
        query = '-date --after "2015-06-22" -assignment "%s" -onlyfinal %s'
        self.API.querify(query % (self.assignment_name, 'true'))
        self.API.querify(query % (self.assignment_name, 'false'))

    def test_flag_onlybackup(self):
        """ Testing if onlybackup flag operates without error """
        query = '-assignment "%s" -onlybackup %s'
        self.API.querify(query % (self.assignment_name, 'true'))
        self.API.querify(query % (self.assignment_name, 'false'))
        


if __name__ == '__main__':
    unittest.main()
