#!/usr/bin/env python
# encoding: utf-8
"""
simple_db_tests.py

This module runs basic tests on the MySQL database.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..')))
import unittest

from google.appengine.ext import testbed

from flask.ext.testing import TestCase #pylint: disable=import-error, no-name-in-module
from flask import Flask

import app
from app.models import db

class BaseTestCase(TestCase):

    def create_app(self): #pylint: disable=no-self-use
        """
        Creates the app
        """
        app = Flask(__name__)
        app.config.from_object('app.settings.Testing')
        return app

    def setUp(self):
        # Flask apps testing. See: http://flask.pocoo.org/docs/testing/
        self.app_import = app
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        db.create_all()

    def tearDown(self):
        self.testbed.deactivate()
        db.session.remove()
        db.drop_all()

    def setCurrentUser(self, email, user_id, is_admin=False):
        os.environ['USER_EMAIL'] = email or ''
        os.environ['USER_ID'] = user_id or ''
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'
