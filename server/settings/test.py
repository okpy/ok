ENV = 'test'
SECRET_KEY = 'samplekey'

DEBUG = True
TESTING = True
ASSETS_DEBUG = True
TESTING_LOGIN = True
DEBUG_TB_INTERCEPT_REDIRECTS = False

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://okdev:okdev@db/okdev'

CACHE_TYPE = 'redis'
CACHE_REDIS_URL = 'redis://redis:6379/0'
CACHE_KEY_PREFIX = 'ok-server'

RQ_LOW_URL = 'redis://redis:6379/1'

GOOGLE_CONSUMER_KEY = ''
