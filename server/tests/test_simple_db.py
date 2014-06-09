#!/usr/bin/env python
# encoding: utf-8
"""
simple_db_tests.py

This module runs basic tests on the MySQL database.
"""
from basetest import BaseTestCase

class TrivialTestCase(BaseTestCase): #pylint: disable=R0904
    """
    Performs extremely simple database operations
    """

    def test_db_create_user(self):
        """
        Creates test user and deletes it
        """
        db = self.app.models.db
        model = self.app.models
        constants = self.app.constants

        test_user = model.User("sharad@sharad.com", "cs61a-tt",
                               constants.ADMIN_ROLE, "Sharad", "Vikram")
        db.session.add(test_user)
        db.session.commit()

        query_user = model.User.query.filter_by(email=
                                                "sharad@sharad.com").first()

        self.assertTrue(query_user is test_user)

        db.session.delete(test_user)
        db.session.commit()

        query_user = model.User.query.filter_by(email=
                                                "sharad@sharad.com").first()

        self.assertTrue(query_user is None)
