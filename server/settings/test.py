import os

ENV = 'test'
SECRET_KEY = os.getenv('OK_SESSION_KEY', 'testkey')

DEBUG = False
ASSETS_DEBUG = False
TESTING_LOGIN = True
DEBUG_TB_INTERCEPT_REDIRECTS = False
INSTANTCLICK = False

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///../oktest.db')
WTF_CSRF_CHECK_DEFAULT = False
WTF_CSRF_ENABLED = False

CACHE_TYPE = 'simple'

RQ_DEFAULT_HOST = REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = 6379
RQ_POLL_INTERVAL = 2000
RQ_DEFAULT_DB = 2  # to prevent conflicts with development

GOOGLE_CONSUMER_KEY = ''
