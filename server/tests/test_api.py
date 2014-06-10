#!/usr/bin/env python
# encoding: utf-8
"""
tests.py

"""
import unittest

from basetest import BaseTestCase #pylint: disable=relative-import

from app.api import API_PREFIX
from app import models

class SimpleTestCase(BaseTestCase): #pylint: disable=no-init
    """
    Simple test case for the API
    """
    def setUp(self): #pylint: disable=super-on-old-class
        super(SimpleTestCase, self).setUp()
        self.user = models.User(email='test@example.com')

    def api_get(self, url, *args, **kwds):
        """
        Utility method to do a get request
        """
        return self.client.get(API_PREFIX + url, *args, **kwds) #pylint: disable=no-member

    def test_users_index_empty(self):
        """ Tests there are no users when the db is created """
        response = self.api_get('/users')
        assert response.status == 200
        assert response.json == []

    def test_users_index_when_one_added(self):
        """ Tests that the index method gives me a user I add """
        models.db.session.add(self.user)
        models.db.session.commit()
        response = self.api_get('/users')
        assert response.status == 200
        assert response.json == [self.user.to_json()]

    def test_add_user_and_get(self):
        """ Tests that getting an ID for a known user gives me that user"""
        models.db.session.add(self.user)
        models.db.session.commit()
        response = self.api_get('/users/{}'.format(self.user.user_id))
        assert response.status == 200
        assert response.json == self.user.to_json()

    def test_get_invalid_id_errors(self):
        """ Tests that a get on an invalid ID errors """
        response = self.api_get('/users/1')
        assert response.status == 404

if __name__ == '__main__':
    unittest.main()
