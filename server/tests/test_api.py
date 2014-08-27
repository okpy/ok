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

from test_base import APIBaseTestCase, unittest #pylint: disable=relative-import

from google.appengine.ext import ndb

from app import models
from app.constants import ADMIN_ROLE

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

        Sets up the authenticator stub, and logs you in as an admin."""
        super(APITest, self).setUp()
        self.login('dummy_admin')

    def get_accounts(self):
        return {
            "dummy_admin": models.User(
                key=ndb.Key("User", "dummy@admin.com"),
                email="dummy@admin.com",
                first_name="Admin",
                last_name="Jones",
                login="albert",
                role=ADMIN_ROLE
            ),
            "dummy_student": models.User(
                key=ndb.Key("User", "dummy@student.com"),
                email="dummy@student.com",
                first_name="Student",
                last_name="Jones",
                login="billy",
            )

        }

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

    def test_pagination(self, total_objects=50, num_page=30):
        """
        Tests that pagination works by making 2 requests.
        """
        insts = []
        for _ in range(total_objects):
            inst = self.get_basic_instance(mutate=True)
            insts.append(inst)
            inst.put()
        while total_objects > 0:
            if hasattr(self, 'forward_cursor'):
                self.get_index(cursor=self.forward_cursor, num_page=num_page)
            else:
                self.get_index(num_page=num_page)
            num_instances = len(self.response_json)
            if self.name == 'user' and num_instances < num_page:
                total_objects += 1 # To take care of the dummy already there
            self.assertTrue(num_instances <= num_page,
                "There are too many instances returned. There are " + str(num_instances) + " instances")
            self.assertTrue(num_instances == min(total_objects, num_page), 
                    "Not right number returned: " + str(total_objects) + " vs. " +str(num_instances) + str(self.response_json))
            total_objects -= num_page

    def test_pagination_single_page(self):
        """
        Tests that pagination works for a single page.
        """
        self.test_pagination(11, 10)
    
    def test_pagination_multiple(self):
        """
        Tests that pagination works for more than 2 pages.
        """
        self.test_pagination(32, 10)

    def test_pagination_exact(self):
        """
        Tests that pagination works for exactly # of entries per page as max.
        """
        self.test_pagination(10, 10)

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

    def test_get_non_admin(self):
        """Tests that a get with a student access token fails."""
        self.logout()
        self.get('/{}/1'.format(self.name))
        self.assertStatusCode(404)

    ## ENTITY POST ##

    def test_entity_create_basic(self):
        """Tests creating an empty entity."""
        inst = self.get_basic_instance(mutate=True)
        self.post_entity(inst)
        self.assertStatusCode(200)

        gotten = self.model.get_by_id(self.response_json['key'])
        self.assertEqual(gotten.key, inst.key)

    def test_create_two_entities(self):
        inst = self.get_basic_instance(mutate=True)
        self.post_entity(inst)
        self.assertStatusCode(200)
        gotten = self.model.get_by_id(self.response_json['key'])

        inst2 = self.get_basic_instance(mutate=True)
        self.post_entity(inst2)
        self.assertStatusCode(200)
        gotten2 = self.model.get_by_id(self.response_json['key'])

        self.assertEqual(gotten.key, inst.key)
        self.assertEqual(gotten2.key, inst2.key)

    ## ENTITY PUT ##

    ## ENTITY DELETE ##

class UserAPITest(APITest, APIBaseTestCase):
    model = models.User
    name = 'user'
    access_token = 'dummy_student'
    num = 1

    @classmethod
    def get_basic_instance(cls, mutate=False):
        if mutate:
            email = str(cls.num) + "test@example.com"
            cls.num += 1
            return models.User(
                key=ndb.Key('User', email),
                email=email,
                first_name="Test",
                last_name="User",
                login="aotnehu"
            )
        else:
            return cls.accounts['dummy_student']

    def test_index_empty(self):
        """This test doesn't make sense for the user API."""

    def test_get_invalid_id_errors(self):
        """Tests that a get on an invalid ID errors."""
        self.get('/{}/4'.format(self.name))
        self.assertStatusCode(404)

    def test_index_one_added(self):
        """Tests that the index method gives the added entity."""
        inst = self.get_basic_instance()
        inst.put()

        self.get_index()
        self.assertTrue(inst.to_json() in self.response_json)
        return inst


    def test_index_one_removed(self):
        """Tests that removing an entity makes it disappear from the index."""
        inst = self.test_index_one_added()

        inst.key.delete()
        self.get_index()
        self.assertTrue(inst.to_json() not in self.response_json)


class AssignmentAPITest(APITest, APIBaseTestCase):
    model = models.Assignment
    name = 'assignment'
    num = 1
    access_token = 'dummy_admin'

    @classmethod
    def get_basic_instance(cls, mutate=True):
        name = 'proj'
        if mutate:
            name += str(cls.num)
            cls.num += 1
        rval = models.Assignment(name=name, points=3)
        return rval

class SubmissionAPITest(APITest, APIBaseTestCase):
    model = models.Submission
    name = 'submission'
    access_token = "submitter"

    num = 1
    def setUp(self):
        super(SubmissionAPITest, self).setUp()
        self.assignment_name = u'test assignment'
        self._assign = models.Assignment(name=self.assignment_name, points=3)
        self._assign.put()
        self._submitter = self.accounts['dummy_student']
        self.logout()
        self.login('dummy_student')

    def get_basic_instance(self, mutate=True):
        message = "{}"
        if mutate:
            message = '{"value":' + str(self.num) + '}'
            self.num += 1
        rval = models.Submission(
            messages=message, submitter=self._submitter.key,
            assignment=self._assign.key)
        return rval

    def post_entity(self, inst, *args, **kwds):
        """Posts an entity to the server."""
        data = inst.to_json()
        data['assignment'] = kwds.pop('assignment', self.assignment_name)
        del data['created']

        self.post_json('/{}/new'.format(self.name),
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
        del self.assignment_name


if __name__ == '__main__':
    unittest.main()

