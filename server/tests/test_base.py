#!/usr/bin/env python
# encoding: utf-8

"""
Server test case scaffolding
"""

import os
import sys
import collections
import urllib

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))

from flask import json

from google.appengine.ext import testbed

try:
    import unittest2 as unittest
except ImportError:
    import unittest
import urllib
import urlparse

from google.appengine.ext import ndb

import app
from app import models
from app import auth
from app.constants import API_PREFIX #pylint: disable=import-error
from app.authenticator import Authenticator, AuthenticationException

class BaseTestCase(unittest.TestCase): #pylint: disable=no-init
    """
    Base test case.
    """
    def setUp(self): #pylint: disable=invalid-name, missing-docstring
        # Flask apps testing. See: http://flask.pocoo.org/docs/testing/
        app.app.config.from_object('app.settings.Debug')
        self.app = app.app
        self.client = self.app.test_client()

        self.app_import = app
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_taskqueue_stub()

    def tearDown(self): #pylint: disable=invalid-name, missing-docstring
        self.testbed.deactivate()


class APIBaseTestCase(BaseTestCase):
    """
    Base API test case. Includes a bunch of useful helper methods.
    """
    model = None
    name = ""
    num = 1
    api_version = 'v1'

    def get_accounts(self):
        """
        Returns the accounts you want to exist in your system.
        """
        raise NotImplementedError

    def setUp(self):
        super(APIBaseTestCase, self).setUp()
        APIBaseTestCase.accounts = self.get_accounts()
        self.user = None
        auth.authenticate = self.authenticate

    def authenticate(self):
        return self.user

    def login(self, user):
        """ Logs in the user. """
        assert not self.user and user in self.accounts
        user = self.accounts[user]
        self.user = user
        user.put()

    def logout(self):
        """ Logs out the user. """
        if self.user in self.accounts.values():
            self.user.key.delete()
        self.user = None

    def get(self, url, *args, **kwds):
        """
        Makes a get request.
        """
        url = API_PREFIX + '/' + self.api_version + url
        params = urllib.urlencode(kwds)
        self.response = self.client.get(url + '?' + params, *args)
        try:
            response_json = json.loads(self.response.data)['data']
            self.response_json = models.json.loads(json.dumps(response_json))
        except ValueError:
            self.response_json = None

    def get_index(self, *args, **kwds):
        """
        Makes a get request on the index.
        Properly creates URL arguments for pagination.
        """
        self.get('/{}'.format(self.name), *args, **kwds)

        if self.response_json:
            self.page = self.response_json['page']
            self.more = self.response_json['more']
            self.response_json = self.response_json['results']

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
        method = kwds.pop('method', None)
        if method:
            mthd = getattr(self.client, method.lower())
        else:
            mthd = self.client.post

        url = API_PREFIX + '/' + self.api_version + url
        self.response = mthd(url, *args, **kwds)
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
            data = data.to_json()

        if isinstance(data, dict):
            data = models.json.dumps(data)
        kwds['data'] = data
        kwds.setdefault('content_type', 'application/json')
        self.post(url, *args, **kwds)

    def post_entity(self, inst, *args, **kwds):
        """
        Posts an entity to the server.
        """
        self.post_json('/{}'.format(self.name), data=inst, *args, **kwds)
        if self.response_json and 'key' in self.response_json:
            if inst.key:
                self.assertEqual(inst.key.id(), self.response_json['key'])
            else:
                inst.key = models.ndb.Key(self.model, self.response_json['key'])
        self.assertStatusCode(201)

    ## ASSERTS ##
    def assertHeader(self, header, value): #pylint: disable=invalid-name
        """Asserts a particular header."""
        self.assertEqual(self.response.headers[header], value)

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
        if isinstance(correct_json, collections.Iterable):
            self.assertItemsEqual(self.response_json, correct_json)
        else:
            self.assertEqual(self.response_json, correct_json)

    def assertEntity(self, inst):
        self.assertJson(inst.to_json())

