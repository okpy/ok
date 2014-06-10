#!/usr/bin/env python
# encoding: utf-8
"""
tests.py

"""
import unittest

from basetest import BaseTestCase #pylint: disable=relative-import

from app.api import API_PREFIX
from app import models

SESSION = models.db.session

class APITest(BaseTestCase): #pylint: disable=no-init
    """
    Simple test case for the API
    """
    @classmethod
    def setUpClass(cls):
        if cls is APITest:
            raise unittest.SkipTest("Skip APITest tests, it's a base class")
        super(APITest, cls).setUpClass()

    def setUp(self): #pylint: disable=super-on-old-class
        super(APITest, self).setUp()
        self.inst = self.model()

    def get(self, url, *args, **kwds):
        """
        Utility method to do a get request
        """
        self.response = self.client.get(API_PREFIX + url, *args, **kwds) #pylint: disable=no-member

    def assertStatusCode(self, code):
        self.assertEqual(self.response.status_code, code)

    def assertJson(self, correct_json):
        self.assertStatusCode(200)
        self.assertEqual(self.response.json, correct_json)

    ## INDEX ##
    def test_index_empty(self):
        """ Tests there are no entities when the db is created """
        response = self.get('/{}'.format(self.name))
        self.assertJson([])

    def test_index_when_one_added(self):
        """ Tests that the index method gives me an entity I add """
        SESSION.add(self.inst)
        SESSION.commit()
        response = self.get('/{}'.format(self.name))
        self.assertJson([self.inst.to_json()])

    def test_index_when_one_removed(self):
        """Tests that removing an entity makes it disappear from the index """
        SESSION.add(self.inst)
        SESSION.commit()
        response = self.get('/{}'.format(self.name))
        self.assertJson([self.inst.to_json()])

        SESSION.delete(self.inst)
        SESSION.commit()
        response = self.get('/{}'.format(self.name))
        self.assertJson([])

    def test_index_when_one_removed_from_two(self):
        SESSION.add(self.inst)
        inst2 = self.model()
        SESSION.add(inst2)
        SESSION.commit()
        response = self.get('/{}'.format(self.name))
        self.assertJson([self.inst.to_json(), inst2.to_json()])

        SESSION.delete(inst2)
        SESSION.commit()
        response = self.get('/{}'.format(self.name))
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

        response = self.get('/{}/{}'.format(self.name, inst2.db_id))
        self.assertJson(inst2.to_json())

    def test_get_invalid_id_errors(self):
        """ Tests that a get on an invalid ID errors """
        self.get('/{}/1'.format(self.name))
        self.assertStatusCode(404)

    ## ENTITY POST ##

    ## ENTITY PUT ##

    ## ENTITY DELETE ##

class UserAPITest(APITest):
    model = models.User
    name = 'users'

if __name__ == '__main__':
    unittest.main()
