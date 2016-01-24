#! ../env/bin/python
# -*- coding: utf-8 -*-
from server import create_app


class TestConfig:
    def test_dev_config(self):
        """ Tests if the development config loads correctly """

        app = create_app('server.settings.dev.DevConfig')
        dev_db = 'sqlite:///../database.db'

        assert app.config['DEBUG'] is True
        assert app.config['SQLALCHEMY_DATABASE_URI'] == dev_db
        assert app.config['CACHE_TYPE'] == 'simple'

    def test_test_config(self):
        """ Tests if the test config loads correctly """

        app = create_app('server.settings.test.TestConfig')
        test_db = 'sqlite:///../database.db'

        assert app.config['DEBUG'] is True
        assert app.config['SQLALCHEMY_DATABASE_URI'] == test_db
        assert app.config['CACHE_TYPE'] == 'simple'
