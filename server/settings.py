# TODO @Sumukh Better Secret Management System

class TestConfig(object):
    DEBUG = True
    SECRET_KEY = 'Testing*ok*server*'
    RESTFUL_JSON = {'indent': 4}
    TESTING_LOGIN = True  # Do NOT turn on for prod

class DevConfig(TestConfig):
    ENV = 'dev'
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost:5432/okdev'

    CACHE_TYPE = 'simple'
    ASSETS_DEBUG = True

class TestConfig(TestConfig):
    ENV = 'test'
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost:5432/okdev'
    SQLALCHEMY_ECHO = True

    CACHE_TYPE = 'simple'
    WTF_CSRF_ENABLED = False

class Config:
    SECRET_KEY = 'samplekey'

class ProdConfig(Config):
    # TODO Move to secret file
    ENV = 'prod'
    SQLALCHEMY_DATABASE_URI = 'postgresql://user:@localhost:5432/okprod'
    CACHE_TYPE = 'simple'
