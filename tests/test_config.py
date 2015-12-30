#! ../env/bin/python
# -*- coding: utf-8 -*-
from server import create_app


class TestConfig:
    def test_dev_config(self):
        """ Tests if the development config loads correctly """

        app = create_app('server.settings.DevConfig')
        test_db = 'sqlite:///../database.db'

        assert app.config['DEBUG'] is True
        assert app.config['SQLALCHEMY_DATABASE_URI'] == test_db
        assert app.config['CACHE_TYPE'] == 'null'

    def test_test_config(self):
        """ Tests if the test config loads correctly """

        app = create_app('server.settings.TestConfig')

        assert app.config['DEBUG'] is True
        assert app.config['SQLALCHEMY_ECHO'] is True
        assert app.config['CACHE_TYPE'] == 'null'

    def test_prod_config(self):
        """ Tests if the production config loads correctly """

        app = create_app('server.settings.ProdConfig')
        prod_db = 'sqlite:///../database.db'
        assert app.config['SQLALCHEMY_DATABASE_URI'] == prod_db
        assert app.config['CACHE_TYPE'] == 'simple'
