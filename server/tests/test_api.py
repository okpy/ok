#!/usr/bin/env python
# encoding: utf-8
#pylint: disable=no-member, no-init
"""
tests.py

"""
import unittest

from basetest import BaseTestCase #pylint: disable=relative-import

from app.api import API_PREFIX
from app import models, constants

SESSION = models.db.session

class APITest(BaseTestCase): #pylint: disable=no-init
    """
    Simple test case for the API
    """
    model = models.declarative_base
    name = ""

    @classmethod
    def get_basic_instance(cls):
        """
        Gets a basic instance of the model class
        """
        raise NotImplementedError()

    @classmethod
    def setUpClass(cls): #pylint: disable=invalid-name
        """Skip testing base class """
        if cls is APITest:
            raise unittest.SkipTest("Skip APITest; it's a base class")
        super(APITest, cls).setUpClass()

    def setUp(self): #pylint: disable=super-on-old-class
        """Set up"""
        super(APITest, self).setUp()
        self.inst = self.model()

    def get(self, url, *args, **kwds):
        """
        Utility method to do a get request
        """
        self.response = self.client.get(API_PREFIX + url, *args, **kwds)

    def post(self, url, *args, **kwds):
        """
        Utility method to do a post request, with json
        """
        kwds.setdefault('content_type', 'application/json')
        self.response = self.client.post(API_PREFIX + url, *args, **kwds)

    def post(self, url, *args, **kwds):
        """
        Utility method to do a post request, with json
        """
        kwds.setdefault('content_type', 'application/json')
        self.response = self.client.post(API_PREFIX + url, *args, **kwds)

    ## ASSERTS ##

    def assertStatusCode(self, code): #pylint: disable=invalid-name
        """ Asserts that the status code was `code`"""
        self.assertEqual(self.response.status_code, code)

    def assertJson(self, correct_json): #pylint: disable=invalid-name
        """Asserts that the response was `correct_json`"""
        self.assertStatusCode(200)
        self.assertEqual(self.response.json, correct_json) #pylint: disable=no-member

    ## INDEX ##
    def test_index_empty(self):
        """ Tests there are no entities when the db is created """
        self.get('/{}'.format(self.name))
        self.assertJson([])

    def test_index_one_added(self):
        """ Tests that the index method gives me an entity I add """
        SESSION.add(self.inst)
        SESSION.commit()
        self.get('/{}'.format(self.name))
        self.assertJson([self.inst.to_json()])

    def test_index_one_removed(self):
        """Tests that removing an entity makes it disappear from the index """
        SESSION.add(self.inst)
        SESSION.commit()
        self.get('/{}'.format(self.name))
        self.assertJson([self.inst.to_json()])

        SESSION.delete(self.inst)
        SESSION.commit()
        self.get('/{}'.format(self.name))
        self.assertJson([])

    def test_index_one_removed_from_two(self):
        """
        Test that removing one item out of two in the DB makes sure
        the other item is still found"""
        SESSION.add(self.inst)
        inst2 = self.model()
        SESSION.add(inst2)
        SESSION.commit()
        self.get('/{}'.format(self.name))
        self.assertJson([self.inst.to_json(), inst2.to_json()])

        SESSION.delete(inst2)
        SESSION.commit()
        self.get('/{}'.format(self.name))
        self.assertJson([self.inst.to_json()])

    ## ENTITY GET ##
    def test_get_basic(self):
        """ Tests that a basic get works """
        SESSION.add(self.inst)
        SESSION.commit()
        self.get('/{}/{}'.format(self.name, self.inst.db_id))
        self.assertJson(self.inst.to_json())

    def test_get_with_two_entities(self):
        """
        Testing that getting one entity with two in the DB gives the
        right one """
        SESSION.add(self.inst)
        inst2 = self.model()
        SESSION.add(inst2)
        SESSION.commit()

        self.get('/{}/{}'.format(self.name, inst2.db_id))
        self.assertJson(inst2.to_json())

    def test_get_invalid_id_errors(self):
        """ Tests that a get on an invalid ID errors """
        self.get('/{}/1'.format(self.name))
        self.assertStatusCode(404)

    ## ENTITY POST ##
    def test_entity_create_basic(self):
        """Basic test to see if you can create an empty entity"""
        inst = self.__class__.get_basic_instance()
        self.post('/{}/new'.format(self.name),
                  data=models.json.dumps(inst.to_json()))
        self.assertStatusCode(200)
        inst.db_id = self.response.json['id']
        gotten = models.User.query.get(self.response.json['id'])
        self.assertEqual(gotten, inst)

    ## ENTITY PUT ##

    ## ENTITY DELETE ##

class UserAPITest(APITest):
    """User API test"""
    model = models.User
    name = 'users'

    @classmethod
    def get_basic_instance(cls):
        return models.User(email=u'test@example.com', login=u'cs61a-ab',
                           role=constants.STUDENT_ROLE, first_name=u"Joe",
                           last_name=u"Schmoe")

class AssignmentAPITest(APITest):
    """ Assignment API test"""
    model = models.Assignment
    name = 'assignments'

    @classmethod
    def get_basic_instance(cls):
        return models.Assignment(name='proj1')


if __name__ == '__main__':
    unittest.main()
