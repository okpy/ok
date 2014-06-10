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

from google.appengine.ext import testbed

from flask.ext.testing import TestCase #pylint: disable=import-error, no-name-in-module
from flask import Flask

import app
from app.models import db

class BaseTestCase(TestCase): #pylint: disable=no-init

    def create_app(self): #pylint: disable=no-self-use
        """
        Creates the app
        """
        app.app.config.from_object('app.settings.Testing')
        return app.app

    def setUp(self): #pylint: disable=invalid-name, missing-docstring
        # Flask apps testing. See: http://flask.pocoo.org/docs/testing/
        self.app_import = app
        self.testbed = testbed.Testbed()
        self.testbed.activate()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_user_stub()
        self.testbed.init_memcache_stub()
        db.create_all()

    def tearDown(self): #pylint: disable=invalid-name, missing-docstring
        self.testbed.deactivate()
        db.session.remove()
        db.drop_all()

    def set_current_user(self, email, user_id, is_admin=False): #pylint: disable=no-self-use
        os.environ['USER_EMAIL'] = email or ''
        os.environ['USER_ID'] = user_id or ''
        os.environ['USER_IS_ADMIN'] = '1' if is_admin else '0'
