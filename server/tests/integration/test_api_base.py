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
from test_base import make_fake_assignment, make_fake_course, make_fake_backup, make_fake_submission, make_fake_finalsubmission #pylint: disable=relative-import
from google.appengine.ext import ndb
from app import models, constants, utils
from ddt import ddt, data, unpack
from app.exceptions import *

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


if __name__ == '__main__':
    unittest.main()
