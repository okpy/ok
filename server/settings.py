# TODO @Sumukh Better Secret Management System
try:
    from secret_keys import ProdConfig  # NOQA
    from secret_keys import google_creds
except ImportError as e:
    google_creds = {
        'GOOGLE_ID': 'fake',
        'GOOGLE_SECRET': 'fake'
    }


class TestConfig(object):
    SECRET_KEY = 'Testing*ok*server*'
    RESTFUL_JSON = {'indent': 4}


class DevConfig(TestConfig):
    ENV = 'dev'
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost:5432/okdev'

    CACHE_TYPE = 'null'
    ASSETS_DEBUG = True


class TestConfig(TestConfig):
    ENV = 'test'
    DEBUG = True
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost:5432/okdev'
    SQLALCHEMY_ECHO = True

    CACHE_TYPE = 'null'
    WTF_CSRF_ENABLED = False
