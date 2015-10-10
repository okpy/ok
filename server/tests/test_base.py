#!/usr/bin/env python
# encoding: utf-8

#pylint: disable=no-init,invalid-name,missing-docstring,maybe-no-member

"""
Server test case scaffolding
"""
import inspect

import os
import sys
import collections
import urllib
import datetime

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
from google.appengine.api import users

import app
from app import models
from app import auth
from app.constants import API_PREFIX
from app import api, utils
from app.authenticator import Authenticator, AuthenticationException


def make_fake_course(creator):
    return models.Course(
        institution="UC Soumya",
        instructor=[creator.key],
        offering="cal/cs61a/fa14",
        active=True)


def make_fake_assignment(course, creator):
    return models.Assignment(
        name='hw1',
        points=3,
        display_name="CS 61A",
        templates="[]",
        course=course.key,
        creator=creator.key,
        max_group_size=4,
        due_date=datetime.datetime.now(),
        lock_date=datetime.datetime.now()+datetime.timedelta(days=1))


def make_fake_backup(assignment, user):
    rval = models.Backup(
        submitter=user.key,
        assignment=assignment.key)
    rval.put()
    return rval


def make_fake_submission(backup):
    rval = models.Submission(backup=backup.key, server_time=datetime.datetime.now())
    rval.put()
    return rval


def make_fake_finalsubmission(submission, assignment, user):
    rval = models.FinalSubmission(
        submission=submission.key,
        submitter=user.key,
        assignment=assignment.key)
    rval.put()
    return rval

def make_fake_queue(assignment, user):
    rval = models.Queue(
        owner=user.key,
        assigned_staff=[user.key],
        assignment=assignment.key)
    rval.put()
    return rval


def make_fake_group(assignment, *args):
    rval = models.Group(
        member=[u.key for u in args],
        assignment=assignment.key
    )
    rval.put()
    return rval


class Mock(object):
    """ To temporarily replace variables - as a with block """

    old = None

    def __init__(self, obj, attr):
        super(Mock, self).__init__()
        self.obj = obj
        self.attr = attr
        self.old = getattr(obj, attr)

    def __enter__(self):
        return self.obj

    def using(self, val):
        setattr(self.obj, self.attr, val)
        return self

    def __exit__(self, type, value, traceback):
        setattr(self.obj, self.attr, self.old)


def mock(obj, attr, new, typecast=None):
    """ To temporarily replace variables - as a decorator """
    old = getattr(obj, attr)
    if callable(typecast):
        setattr(obj, attr, typecast(new))
    else:
        setattr(obj, attr, new)

    def decorator(f):
        def helper(*args, **kwargs):
            try:
                response = f(*args, **kwargs)
            finally:
                if callable(typecast):
                    setattr(obj, attr, typecast(old))
                else:
                    setattr(obj, attr, old)
            return response
        helper.__name__ = f.__name__
        return helper
    return decorator


class TestingError(Exception):
    pass


class BaseTestCase(unittest.TestCase):
    """
    Base test case.
    """
    def setUp(self):
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
        self.taskqueue_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
        self._typecast = None
        self._mocks = []

    def tearDown(self): #pylint: disable=invalid-name, missing-docstring
        self.testbed.deactivate()
        for obj, attr, val in self._mocks:
            if callable(self._typecast):
                setattr(obj, attr, self._typecast(val))
            else:
                setattr(obj, attr, val)

    def mock(self, obj, attr):
        """ Utility - mock an attr for the duration of the test method """
        self._mocks.append((obj, attr, getattr(obj, attr)))

        def using(val, typecast=None):
            if callable(typecast):
                self._typecast = typecast
                setattr(obj, attr, typecast(val))
            else:
                setattr(obj, attr, val)
        return self.obj().set(using=using)

    @staticmethod
    def obj():
        """ Utility - object with set(k=v, k2=v2) method """
        class Obj:
            def set(self, **kwargs):
                [setattr(self, k, v) for k, v in kwargs.items()]
                return self
        return Obj()

    @staticmethod
    def always_can():
        """ Utility - object that always allows user """
        return BaseTestCase.obj().set(can=lambda *args, **kwargs: True)

    @staticmethod
    def never_can():
        """ Utility - object that never allows user """
        return BaseTestCase.obj().set(can=lambda *args, **kwargs: False)

    @staticmethod
    def raise_error(error=None, *args, **kwargs):
        """ Raise an error for testing purposes """
        if inspect.isclass(error) and issubclass(error, Exception):
            def raise_error_helper(*args, **kwargs):
                raise error()
            return raise_error_helper
        raise TestingError()


class APIBaseTestCase(BaseTestCase):
    """
    Base API test case. Includes a bunch of useful helper methods.
    """
    model = None
    name = ""
    num = 1
    api_version = 'v1'
    url_prefix = API_PREFIX + '/{}'

    def get_accounts(self):
        """ Returns the accounts you want to exist in your system. """
        raise NotImplementedError

    def setUp(self):
        super(APIBaseTestCase, self).setUp()
        self.accounts = self.get_accounts()
        for acc in self.accounts.values():
            acc.put()

        self.user = None
        auth.authenticate = self.authenticate
        users.get_current_user = self.authenticate_GAE_service

    def authenticate(self):
        return self.user

    def authenticate_GAE_service(self):
        return self.obj().set(
            email=lambda *args: self.user.email[0],
            user_id=lambda *args: self.user.key.id()
        ) if self.user else None

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
        if self.url_prefix:
            url = self.url_prefix.format(self.api_version) + url

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
