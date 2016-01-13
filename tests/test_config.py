#! ../env/bin/python
# -*- coding: utf-8 -*-
from server import create_app


class TestConfig:
    def test_dev_config(self):
        """ Tests if the development config loads correctly """

        app = create_app('server.settings.dev.DevConfig')
        dev_db = 'postgresql://postgres:@localhost:5432/okdev'

        assert app.config['DEBUG'] is True
        assert app.config['SQLALCHEMY_DATABASE_URI'] == dev_db
        assert app.config['CACHE_TYPE'] == 'simple'

    def test_test_config(self):
        """ Tests if the test config loads correctly """

        app = create_app('server.settings.test.TestConfig')
        test_db = 'postgresql://postgres:@localhost:5432/oktest'

        assert app.config['DEBUG'] is True
        assert app.config['SQLALCHEMY_DATABASE_URI'] == test_db
        assert app.config['CACHE_TYPE'] == 'simple'

    def test_prod_config(self):
        """ Tests if the production config loads correctly """

        app = create_app('server.settings.prod.ProdConfig')

        assert 'postgres' in app.config['SQLALCHEMY_DATABASE_URI']
        assert app.config['CACHE_TYPE'] == 'simple'
        assert app.config['SECRET_KEY'] is not None
