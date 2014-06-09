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
        database = self.app_import.models.db
        model = self.app_import.models
        constants = self.app_import.constants

        test_user = model.User(email="sharad@sharad.com", login="cs61a-tt",
                               role=constants.ADMIN_ROLE, first_name="Sharad",
                               last_name="Vikram")
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
