import os

ENV = 'dev'
SECRET_KEY = os.getenv('OK_SESSION_KEY', 'changeinproductionkey')
CACHE_TYPE = 'simple'

MAINTAINENCE = True
DEBUG = False
ASSETS_DEBUG = True
TESTING_LOGIN = True
DEBUG_TB_INTERCEPT_REDIRECTS = False

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = 'sqlite:///../oksqlite.db'
# SQLALCHEMY_ECHO = True

MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # Max Upload Size is 8MB

CACHE_TYPE = 'simple'

GOOGLE_CONSUMER_KEY = ''
