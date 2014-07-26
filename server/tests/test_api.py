#!/usr/bin/env python
# encoding: utf-8
#pylint: disable=no-member, no-init

"""
API tests
"""

import unittest
from flask import json

from test_base import BaseTestCase #pylint: disable=relative-import

from app.api import API_PREFIX
from app import models, constants

class APITest(object): #pylint: disable=no-init
    """
    Simple test case for the API
    """
    model = None
    name = ""
    num = 1

    @classmethod
    def get_basic_instance(cls):
        """
        Gets a basic instance of the model class.
        """
        raise NotImplementedError()

    def setUp(self): #pylint: disable=super-on-old-class, invalid-name
        """Set up the API Test.

        Creates the instance of the model you're API testing."""
        super(APITest, self).setUp()
        self.inst = self.get_basic_instance()

    def get(self, url, *args, **kwds):
        """
        Makes a get request.
        """
        self.response = self.client.get(API_PREFIX + url, *args, **kwds)
        try:
            response_json = json.loads(self.response.data)['data']
            self.response_json = models.json.loads(json.dumps(response_json))
        except Exception as e:
            self.response_json = None

    def get_index(self, *args, **kwds):
        """
        Makes a get request on the index.
        """
        self.get('/{}'.format(self.name), *args, **kwds)

    def get_entity(self, inst, *args, **kwds):
        """
        Makes a get request on a particular instance.
        """
        self.get('/{}/{}'.format(self.name, inst.key.id()), *args, **kwds)

    def post(self, url, *args, **kwds):
        """
        Makes a post request, with json.
        """
        kwds.setdefault('content_type', 'application/json')
        self.response = self.client.post(API_PREFIX + url, *args, **kwds)
        try:
            response_json = json.loads(self.response.data)
            self.response_json = models.json.loads(
                json.dumps(response_json['data']))
        except ValueError:
            self.response_json = None

    def post_json(self, url, *args, **kwds):
        """
        Makes a post request.
        """
        data = kwds.get('data', {})
        if isinstance(data, models.Base):
            data = data.to_dict()
        if isinstance(data, dict):
            data = models.json.dumps(data)
        kwds['data'] = data
        kwds.setdefault('content_type', 'application/json')
        self.post(url, *args, **kwds)

    def post_entity(self, inst, *args, **kwds):
        """
        Posts an entity to the server.
        """
        self.post_json('/{}/new'.format(self.name), data=inst, *args, **kwds)
        if self.response_json and 'key' in self.response_json:
            if inst.key:
                self.assertEqual(inst.key.id(), self.response_json['key'])
            else:
                inst.key = models.ndb.Key(self.model, self.response_json['key'])
        self.assertStatusCode(200)

    def get_by_id(self, key):
        return self.model.get_by_id(key)

    ## ASSERTS ##

    def assertStatusCode(self, code): #pylint: disable=invalid-name
        """Asserts the status code."""
        response_json = json.loads(self.response.data)
        self.assertEqual(self.response.status_code, code,
                         response_json['message'])

    def assertJson(self, correct_json): #pylint: disable=invalid-name
        """Asserts that the response is correct_json."""
        self.assertStatusCode(200)
        self.assertItemsEqual(self.response_json, correct_json)

    ## INDEX ##

    def test_index_empty(self):
        """Tests there are no entities when the db is created."""
        self.get('/{}'.format(self.name))
        self.assertJson([])

    def test_index_one_added(self):
        """Tests that the index method gives the added entity."""
        self.inst.put()
        self.get_index()
        self.assertJson([self.inst.to_json()])

    def test_index_one_removed(self):
        """Tests that removing an entity makes it disappear from the index."""
        self.inst.put()
        self.get_index()
        self.assertJson([self.inst.to_json()])

        self.inst.key.delete()
        self.get_index()
        self.assertJson([])

    def test_index_one_removed_from_two(self):
        """
        Tests that removing one item out of two in the DB makes sure
        the other item is still found.
        """
        self.inst.put()
        inst2 = self.get_basic_instance()
        inst2.put()
        self.get_index()
        self.assertJson(sorted([self.inst.to_json(), inst2.to_json()]))

        inst2.key.delete()
        self.get_index()
        self.assertJson([self.inst.to_json()])

    ## ENTITY GET ##

    def test_get_basic(self):
        """Tests that a basic get works."""
        self.inst.put()
        self.get_entity(self.inst)
        self.assertJson(self.inst.to_json())

    def test_get_with_two_entities(self):
        """
        Tests that getting one entity with two in the DB gives the right one.
        """
        self.inst.put()
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
        self.post_entity(self.inst)
        self.assertStatusCode(200)

        gotten = self.get_by_id(self.response_json['key'])
        self.assertEqual(gotten.key, self.inst.key)

    ## ENTITY PUT ##

    ## ENTITY DELETE ##

class UserAPITest(APITest, BaseTestCase):
    model = models.User
    name = 'user'
    num = 1

    @classmethod
    def get_basic_instance(cls):
        rval = models.User(email=str(cls.num) + u'test@example.com',
                           first_name=u'Joe', last_name=u'Schmoe',
                           role=constants.STUDENT_ROLE)
        cls.num += 1
        return rval

class AssignmentAPITest(APITest, BaseTestCase):
    model = models.Assignment
    name = 'assignment'
    num = 1

    @classmethod
    def get_basic_instance(cls):
        rval = models.Assignment(name=u'proj' + str(cls.num), points=3)
        cls.num += 1
        return rval

class SubmissionAPITest(APITest, BaseTestCase):
    model = models.Submission
    name = 'submission'

    num = 1
    _assign = None

    @classmethod
    def get_assignment(cls):
        if not cls._assign:
            cls.assignment_name = u'test assignment'
            cls._assign = models.Assignment(name=cls.assignment_name, points=3)
            cls._assign.put()
        return cls._assign

    def get_basic_instance(self):
        rval = models.Submission(messages="{}", submitter=None,
                                 assignment=self.get_assignment())
        self.num += 1
        return rval

    def post_entity(self, inst, *args, **kwds):
        """Posts an entity to the server."""
        data = inst.to_dict()
        data['assignment'] = kwds.pop('assignment', self.assignment_name)
        # TODO make this access token somewhat real
        data['access_token'] = 'LETMEIN'
        del data['created']

        self.post_json('/{}/new'.format(self.name), data=data, *args, **kwds)
        if self.response_json and 'key' in self.response_json:
            if inst.key:
                self.assertEqual(inst.key.id(), self.response_json['key'])
            else:
                inst.key = models.ndb.Key(self.model,
                                          self.response_json.get('key'))

    def test_invalid_assignment_name(self):
        self.assignment_name = 'assignment'
        self.post_entity(self.inst)
        self.assertStatusCode(400)

if __name__ == '__main__':
    unittest.main()

