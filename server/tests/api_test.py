#!/usr/bin/env python
# encoding: utf-8
"""
tests.py

"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest

from google.appengine.ext import testbed

from app import app
from app.api import API_PREFIX
from app.models import db

from flask import Flask
from flask.ext.testing import TestCase

class SimpleTestCase(TestCase):
    def create_app(self):
        app = Flask(__name__)
        app.config.from_object('app.settings.Testing')
        return app

    def setUp(self):
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_user_stub()
        db.create_all()

    def tearDown(self):
        self.testbed.deactivate()
        db.session.remove()
        db.drop_all()

    def app_get(self, url, *args, **kwds):
        print API_PREFIX + url
        return self.client.get(API_PREFIX + url, *args, **kwds)

    def setCurrentUser(self, email, user_id, is_admin=False):
        os.environ['USER_EMAIL'] = email or ''
        os.environ['USER_ID'] = user_id or ''
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'

    def test_users_index_empty(self):
        response = self.app_get('/users')
        print response.data
        self.assertEquals(response.json, dict())

if __name__ == '__main__':
    unittest.main()
