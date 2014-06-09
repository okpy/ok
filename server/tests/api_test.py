#!/usr/bin/env python
# encoding: utf-8
"""
tests.py

"""
import unittest

from google.appengine.ext import testbed

from basetest import BaseTestCase

from app.api import API_PREFIX
from app.models import db


class SimpleTestCase(BaseTestCase): #pylint: disable=no-init
    """
    Simple test case for the API
    """
    def app_get(self, url, *args, **kwds):
        """
        Utility method to do a get request
        """
        print API_PREFIX + url
        return self.client.get(API_PREFIX + url, *args, **kwds) #pylint: disable=no-member

    def test_users_index_empty(self):
        """ Tests there are no users when the db is created """
        response = self.app_get('/users')
        print response.data
        self.assertEquals(response.json, dict()) #pylint: disable=no-member

if __name__ == '__main__':
    unittest.main()
