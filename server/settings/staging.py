""" Do not put secrets in this file. This file is public.
    For staging environment (Using Dokku)
"""
import os
import sys
import binascii

from server.settings import RAVEN_IGNORE_EXCEPTIONS

default_secret = binascii.hexlify(os.urandom(24))

ENV = 'staging'
PREFERRED_URL_SCHEME = 'https'

SECRET_KEY = os.getenv('SECRET_KEY', default_secret)
CACHE_TYPE = 'simple'

DEBUG = False
ASSETS_DEBUG = False
TESTING_LOGIN = False
DEBUG_TB_INTERCEPT_REDIRECTS = False

SQLALCHEMY_TRACK_MODIFICATIONS = False
SENTRY_USER_ATTRS = ['email', 'name']

RQ_DEFAULT_HOST = REDIS_HOST = CACHE_REDIS_HOST = \
    os.getenv('REDIS_HOST', 'redis-master')
REDIS_PORT = 6379
RQ_POLL_INTERVAL = 2000
OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 28800

db_url = os.getenv('DATABASE_URL')
if db_url:
    db_url = db_url.replace('mysql://', 'mysql+pymysql://')
    db_url += "&sql_mode=STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION"

else:
    db_url = os.getenv('SQLALCHEMY_URL', 'sqlite:///../oksqlite.db')

SQLALCHEMY_DATABASE_URI = db_url
WTF_CSRF_CHECK_DEFAULT = True
WTF_CSRF_ENABLED = True
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # Max Upload Size is 10MB

STORAGE_PROVIDER = os.environ.get('STORAGE_PROVIDER',  'LOCAL')
STORAGE_SERVER = False
STORAGE_CONTAINER = os.environ.get('STORAGE_CONTAINER',  'ok-v3-user-files')
STORAGE_KEY = os.environ.get('STORAGE_KEY', '')
STORAGE_SECRET = os.environ.get('STORAGE_SECRET', '')

if STORAGE_PROVIDER == 'LOCAL' and not os.path.exists(STORAGE_CONTAINER):
    os.makedirs(STORAGE_CONTAINER)

try:
    os.environ["GOOGLE_ID"]
    os.environ["GOOGLE_SECRET"]
except KeyError:
    print("Please set the google login variables. source secrets.sh")
    sys.exit(1)

GOOGLE = {
    'consumer_key': os.environ.get('GOOGLE_ID'),
    'consumer_secret':  os.environ.get('GOOGLE_SECRET')
}

SENDGRID_AUTH = {
    'user': os.environ.get("SENDGRID_USER"),
    'key': os.environ.get("SENDGRID_KEY")
}
