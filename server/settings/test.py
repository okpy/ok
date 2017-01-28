import os

ENV = 'test'
SECRET_KEY = os.getenv('OK_SESSION_KEY', 'testkey')

DEBUG = False
ASSETS_DEBUG = True
TESTING_LOGIN = True
DEBUG_TB_INTERCEPT_REDIRECTS = False
INSTANTCLICK = False

SQLALCHEMY_TRACK_MODIFICATIONS = False

db_url = os.getenv('DATABASE_URL')
if db_url and 'mysql' in db_url:
    db_url = db_url.replace('mysql://', 'mysql+pymysql://')
    db_url += "&sql_mode=STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION"
else:
    db_url = os.getenv('DATABASE_URL', 'sqlite:///../oktest.db')

SQLALCHEMY_DATABASE_URI = db_url

WTF_CSRF_CHECK_DEFAULT = False
WTF_CSRF_ENABLED = False

STORAGE_PROVIDER = 'LOCAL'
STORAGE_SERVER = False
STORAGE_CONTAINER = os.path.abspath("./local-storage")

if not os.path.exists(STORAGE_CONTAINER):
    os.makedirs(STORAGE_CONTAINER)

CACHE_TYPE = 'simple'

RQ_DEFAULT_HOST = REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = 6379
RQ_POLL_INTERVAL = 2000
RQ_DEFAULT_DB = 2  # to prevent conflicts with development

GOOGLE_CONSUMER_KEY = ''
