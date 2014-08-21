#!/usr/bin/env python
# encoding: utf-8
#pylint: disable=no-member, no-init

"""
API tests
"""

import unittest
import urllib
import urlparse

from flask import json

from test_base import BaseTestCase #pylint: disable=relative-import

from app.constants import API_PREFIX #pylint: disable=import-error
from app import models, constants, authenticator #pylint: disable=import-error
from app import app

class APITest(object): #pylint: disable=no-init
    """
    Simple test case for the API
    """
    model = None
    name = ""
    num = 1
    access_token = 'dummy_student'

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
        app.config["AUTHENTICATOR"] = authenticator.DummyAuthenticator()

    def add_access_token(self, url, kwds):
        access_token = kwds.pop('access_token', self.access_token)
        params = {
            'access_token': access_token
        }
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update(params)
        url_parts[4] = urllib.urlencode(query)
        url = urlparse.urlunparse(url_parts)
        return url

    def get(self, url, *args, **kwds):
        """
        Makes a get request.
        """
        url = self.add_access_token(url, kwds)
        self.response = self.client.get(API_PREFIX + url)
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
        url = self.add_access_token(url, kwds)
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
        inst2 = self.get_basic_instance()
        inst2.put()
        self.get_index()
        self.assertJson(sorted([inst.to_json(), inst2.to_json()]))

        inst2.key.delete()
        self.get_index()
        self.assertJson([inst.to_json()])

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

    def test_get_bad_permissions(self):
        """Tests that a get with an invalid access token fails."""
        self.get('/{}'.format(self.name), access_token='bad_access_token')
        self.assertStatusCode(401)

    def test_get_non_admin(self):
        """Tests that a get with a student access token fails."""
        self.get('/{}'.format(self.name), access_token='dummy_student')
        self.assertStatusCode(401)

    ## ENTITY POST ##

    def test_entity_create_basic(self):
        """Tests creating an empty entity."""
        inst = self.get_basic_instance()
        self.post_entity(inst)
        self.assertStatusCode(200)

        gotten = self.get_by_id(self.response_json['key'])
        self.assertEqual(gotten.key, inst.key)

    ## ENTITY PUT ##

    ## ENTITY DELETE ##

class UserAPITest(APITest, BaseTestCase):
    model = models.User
    name = 'user'
    num = 1
    access_token = 'dummy_admin'

    @classmethod
    def get_basic_instance(cls):
        rval = models.User(email=str(cls.num) + u'test@example.com',
                           first_name=u'Joe', last_name=u'Schmoe',
                           role=constants.STUDENT_ROLE)
        cls.num += 1
        return rval

    def test_index_empty(self):
        """Tests there are no entities when the db is created."""
        self.get('/{}'.format(self.name))
        self.assertStatusCode(200)
        self.assertEqual(len(self.response_json), 1)

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


    def test_index_one_removed_from_two(self):
        """
        Tests that removing one item out of two in the DB makes sure
        the other item is still found.
        """
        inst = self.get_basic_instance()
        inst.put()
        inst2 = self.get_basic_instance()
        inst2.put()
        self.get_index()
        self.assertTrue(inst.to_json() in self.response_json)
        self.assertTrue(inst2.to_json() in self.response_json)

        inst2.key.delete()
        self.get_index()
        self.assertTrue(inst.to_json() in self.response_json)
        self.assertTrue(inst2.to_json() not in self.response_json)

class AssignmentAPITest(APITest, BaseTestCase):
    model = models.Assignment
    name = 'assignment'
    num = 1
    access_token = 'dummy_admin'

    @classmethod
    def get_basic_instance(cls):
        rval = models.Assignment(name=u'proj' + str(cls.num), points=3)
        cls.num += 1
        return rval

class SubmissionAPITest(APITest, BaseTestCase):
    model = models.Submission
    name = 'submission'
    access_token = "submitter"

    num = 1

    def setUp(self):
        super(SubmissionAPITest, self).setUp()
        self.assignment_name = u'test assignment'
        self._assign = models.Assignment(name=self.assignment_name, points=3)
        self._assign.put()
        self._submitter = models.User.get_or_insert(
            '<submitter@gmail.com>',
            email="submitter@gmail.com"
        )
        self._submitter.put()

    def get_basic_instance(self):
        rval = models.Submission(messages="{}", submitter=self._submitter.key,
                                 assignment=self._assign.key)
        self.num += 1
        return rval

    def post_entity(self, inst, *args, **kwds):
        """Posts an entity to the server."""
        data = inst.to_json()
        data['assignment'] = kwds.pop('assignment', self.assignment_name)
        del data['created']
        del data['submitter']

        self.post_json('/{}/new?access_token={}'.format(self.name, self.access_token),
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

    def test_get_non_admin(self):
        """Tests that a get with a student access token works."""
        self.get('/{}'.format(self.name), access_token=self.access_token)
        self.assertStatusCode(200)

    def test_different_user(self):
        """One student can't see another user's submissions."""
        inst = self.get_basic_instance()
        inst.put()
        fake_user = models.User(email='gaga@gmail.com')
        inst2 = models.Submission(messages="{}",
                                  submitter=fake_user.key,
                                  assignment=self._assign.key)
        inst2.put()
        self.get_index()
        self.assertJson([inst.to_json()])
        self.assertTrue(inst2.to_json() not in self.response_json)

if __name__ == '__main__':
    unittest.main()

