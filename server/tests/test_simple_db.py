#!/usr/bin/env python
# encoding: utf-8
"""
simple_db_tests.py

This module runs basic tests on the MySQL database.
"""
import basetest

class TrivialTestCase(basetest.BaseTestCase): #pylint: disable=R0904
    """
    Performs extremely simple database operations
    """

    def test_db_create_user(self):
        """
        Creates test user and deletes it
        """
        database = self.app.models.db
        model = self.app.models
        constants = self.app.constants

        test_user = model.User("sharad@sharad.com", "cs61a-tt",
                               constants.ADMIN_ROLE, "Sharad", "Vikram")
        database.session.add(test_user)
        database.session.commit()

        query_user = model.User.query.filter_by(email= #pylint: disable=no-member
                                                "sharad@sharad.com").first()

        self.assertTrue(query_user is test_user)

        database.session.delete(test_user)
        database.session.commit()

        query_user = model.User.query.filter_by(email= #pylint: disable=no-member
                                                "sharad@sharad.com").first()

        self.assertTrue(query_user is None)
