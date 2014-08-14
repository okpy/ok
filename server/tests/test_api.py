#!/usr/bin/env python
# encoding: utf-8
#pylint: disable=no-member, no-init, too-many-public-methods
#pylint: disable=attribute-defined-outside-init
"""
tests.py

"""

import unittest
import urllib
import urlparse

from flask import json

from test_base import BaseTestCase #pylint: disable=relative-import

from google.appengine.ext import ndb

from app.constants import API_PREFIX, ADMIN_ROLE #pylint: disable=import-error
from app import models, constants, authenticator #pylint: disable=import-error
from app import app
from app.authenticator import Authenticator, AuthenticationException

ACCOUNTS = {
    "dummy_student": lambda: models.User(
        key=ndb.Key("User", "dummy@student.com"),
        email="dummy@student.com",
        first_name="Dummy",
        last_name="Jones",
        login="some13413"
    ),
    "dummy_admin": lambda: models.User(
        key=ndb.Key("User", "dummy@admin.com"),
        email="dummy@admin.com",
        first_name="Admin",
        last_name="Jones",
        login="albert",
        role=ADMIN_ROLE
    ),
}

class DummyAuthenticator(Authenticator):
    def authenticate(self, access_token):
        if access_token in ACCOUNTS:
            return ACCOUNTS[access_token].email
        if access_token == "bad_access_token":
            raise AuthenticationException("access token invalid")
        return "%s@gmail.com" % access_token

    def get_user(self, email):
        return super(DummyAuthenticator, self).get_user(email, "admin" in email)

class APITest(object): #pylint: disable=no-init
    """
    Simple test case for the API
    """
    model = None
    name = ""
    num = 1

    @classmethod
    def get_basic_instance(cls, mutate=False):
        """
        Gets a basic instance of the model class.
        """
        raise NotImplementedError()

    def setUp(self): #pylint: disable=super-on-old-class, invalid-name
        """Set up the API Test.

        Creates the instance of the model you're API testing."""
        super(APITest, self).setUp()
        app.config["AUTHENTICATOR"] = DummyAuthenticator()
        self.user = None
        self.login('dummy_student')

    def login(self, user):
        assert not self.user
        self.user = user
        if user in ACCOUNTS:
            ACCOUNTS[user] = ACCOUNTS[user]()
            ACCOUNTS[user].put()

    def logout(self):
        self.user = None

    def add_access_token(self, url):
        if not self.user:
            return url
        params = {
            'access_token': self.user
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
        url = self.add_access_token(url)
        self.response = self.client.get(API_PREFIX + url)
        try:
            response_json = json.loads(self.response.data)['data']
            self.response_json = models.json.loads(json.dumps(response_json))
        except ValueError:
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
        url = self.add_access_token(url)
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
        try:
            response_json = json.loads(self.response.data)
        except Exception:
            self.assertTrue(False, self.response.data)
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

        gotten = self.get_by_id(self.response_json['key'])
        self.assertEqual(gotten.key, inst.key)

    def test_create_two_entities(self):
        inst = self.get_basic_instance(mutate=True)
        self.post_entity(inst)
        self.assertStatusCode(200)
        gotten = self.get_by_id(self.response_json['key'])

        inst2 = self.get_basic_instance(mutate=True)
        self.post_entity(inst2)
        self.assertStatusCode(200)
        gotten2 = self.get_by_id(self.response_json['key'])

        self.assertEqual(gotten.key, inst.key)
        self.assertEqual(gotten2.key, inst2.key)

    ## ENTITY PUT ##

    ## ENTITY DELETE ##

class UserAPITest(APITest, BaseTestCase):
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
            return ACCOUNTS['dummy_student']

    def test_index_empty(self):
        """
        You can't see any users unless you're logged in, so it doesn't make
        sense to have this test for the User API
        """
        pass


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


class AssignmentAPITest(APITest, BaseTestCase):
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
        self._submitter = ACCOUNTS['dummy_student']
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

