""" Do not put secrets in this file. This file is public.
    Production config.
"""
import os
import sys
import binascii

from server.settings import RAVEN_IGNORE_EXCEPTIONS

default_secret = binascii.hexlify(os.urandom(24))

ENV = 'prod'
PREFERRED_URL_SCHEME = 'https'

if not os.getenv('SECRET_KEY'):
    print("The secret key is not set!!")

SECRET_KEY = os.getenv('SECRET_KEY', default_secret)

DEBUG = False
ASSETS_DEBUG = False
TESTING_LOGIN = False
DEBUG_TB_INTERCEPT_REDIRECTS = False

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

WTF_CSRF_CHECK_DEFAULT = True
WTF_CSRF_ENABLED = True

CACHE_TYPE = 'redis'
CACHE_REDIS_HOST = os.getenv('REDIS_HOST', 'redis-master')
CACHE_KEY_PREFIX = 'ok-web'

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
