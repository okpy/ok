""" Do not put secrets in this file. This file is public.
    Production config.
"""
import os
import sys

from server.settings import RAVEN_IGNORE_EXCEPTIONS

ENV = 'simple'
PREFERRED_URL_SCHEME = 'http'

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = False
ASSETS_DEBUG = False
TESTING_LOGIN = False
DEBUG_TB_INTERCEPT_REDIRECTS = False

db_url = os.getenv('DATABASE_URL')
if db_url:
    if 'mysql' in db_url:
        db_url = db_url.replace('mysql://', 'mysql+pymysql://')
        db_url += "&sql_mode=STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION"
else:
    print("The database URL is not set!")
    db_url = os.getenv('SQLALCHEMY_URL', 'sqlite:///../oksqlite.db')

SQLALCHEMY_DATABASE_URI = db_url

# If using sqlite use absolute path (otherwise we break migrations)
sqlite_prefix = 'sqlite:///'
if SQLALCHEMY_DATABASE_URI.startswith(sqlite_prefix):
    SQLALCHEMY_DATABASE_URI = (sqlite_prefix +
            os.path.abspath(SQLALCHEMY_DATABASE_URI[len(sqlite_prefix) + 1:]))

SQLALCHEMY_TRACK_MODIFICATIONS = False
SENTRY_USER_ATTRS = ['email', 'name']
PREFERRED_URL_SCHEME = 'https'
OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 28800

WTF_CSRF_CHECK_DEFAULT = True
WTF_CSRF_ENABLED = True

CACHE_TYPE = 'simple'
CACHE_KEY_PREFIX = 'ok-web'

RQ_DEFAULT_HOST = REDIS_HOST = CACHE_REDIS_HOST = \
    os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = 6379
RQ_POLL_INTERVAL = 2000

STORAGE_PROVIDER = 'LOCAL'
STORAGE_SERVER = False
STORAGE_CONTAINER = os.path.abspath("./local-storage")

if not os.path.exists(STORAGE_CONTAINER):
    os.makedirs(STORAGE_CONTAINER)
try:
    os.environ["GOOGLE_ID"]
    os.environ["GOOGLE_SECRET"]
except KeyError:
    print("Please set the google login variables.")
    sys.exit(1)

# Service Keys

GOOGLE = {
    'consumer_key': os.environ.get('GOOGLE_ID'),
    'consumer_secret':  os.environ.get('GOOGLE_SECRET')
}

SENDGRID_AUTH = {
    'user': os.environ.get("SENDGRID_USER"),
    'key': os.environ.get("SENDGRID_KEY")
}
