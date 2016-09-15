import os

ENV = 'dev'
SECRET_KEY = os.getenv('OK_SESSION_KEY', 'changeinproductionkey')
CACHE_TYPE = 'simple'

DEBUG = True
ASSETS_DEBUG = True
TESTING_LOGIN = True
DEBUG_TB_INTERCEPT_REDIRECTS = False
INSTANTCLICK = True

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = 'sqlite:///../oksqlite.db'
# SQLALCHEMY_ECHO = True
COMPRESS_MIMETYPES = ['text/html', 'text/css', 'text/csv', 'text/xml', 'application/json', 'application/javascript']

RQ_DEFAULT_HOST = REDIS_HOST = 'localhost'
REDIS_PORT = 6379
RQ_POLL_INTERVAL = 2000

MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # Max Upload Size is 8MB

GOOGLE_CONSUMER_KEY = ''
