
# TODO @Sumukh Better Secret Management System
try:
    from secret_keys import ProdConfig  # NOQA
except ImportError as e:
    pass


class TestConfig(object):
    SECRET_KEY = 'Testing*ok*server*'


class DevConfig(TestConfig):
    ENV = 'dev'
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://okdev:@localhost:5432/okdev'

    CACHE_TYPE = 'null'
    ASSETS_DEBUG = True


class TestConfig(TestConfig):
    ENV = 'test'
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    SQLALCHEMY_DATABASE_URI = 'postgresql://okdev:@localhost:5432/okdev'
    SQLALCHEMY_ECHO = True

    CACHE_TYPE = 'null'
    WTF_CSRF_ENABLED = False
