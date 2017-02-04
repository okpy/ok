""" Do not put secrets in this file. This file is public.
    Production config.
"""
import os
import sys

from server.settings import RAVEN_IGNORE_EXCEPTIONS

ENV = 'prod'
PREFERRED_URL_SCHEME = 'https'

SECRET_KEY = os.getenv('SECRET_KEY')

DEBUG = False
ASSETS_DEBUG = False
TESTING_LOGIN = False
DEBUG_TB_INTERCEPT_REDIRECTS = False
# The Google Cloud load balancer behaves like two proxies: one with the external
# fowarding rule IP, and one with an internal IP.
# See https://cloud.google.com/compute/docs/load-balancing/http/#target_proxies
# Including Nginx too makes 3 proxies.
NUM_PROXIES = 3

db_url = os.getenv('DATABASE_URL')
if db_url:
    db_url = db_url.replace('mysql://', 'mysql+pymysql://')
    db_url += "&sql_mode=STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION"
else:
    print("The database URL is not set!")
    sys.exit(1)

SQLALCHEMY_DATABASE_URI = db_url
SQLALCHEMY_TRACK_MODIFICATIONS = False
SENTRY_USER_ATTRS = ['email', 'name']
PREFERRED_URL_SCHEME = 'https'
OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 28800

WTF_CSRF_CHECK_DEFAULT = True
WTF_CSRF_ENABLED = True

MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # Max Upload Size is 20

CACHE_TYPE = 'redis'
CACHE_KEY_PREFIX = 'ok-web'

RQ_DEFAULT_HOST = REDIS_HOST = CACHE_REDIS_HOST = \
    os.getenv('REDIS_HOST', 'redis-master')
REDIS_PORT = 6379
RQ_POLL_INTERVAL = 2000

STORAGE_PROVIDER = os.environ.get('STORAGE_PROVIDER',  'GOOGLE_STORAGE')
STORAGE_SERVER = False
STORAGE_CONTAINER = os.environ.get('STORAGE_CONTAINER',  'ok-v3-user-files')
STORAGE_KEY = os.environ.get('STORAGE_KEY', '')
STORAGE_SECRET = os.environ.get('STORAGE_SECRET', '')

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
