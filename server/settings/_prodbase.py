import os

from server.settings import RAVEN_IGNORE_EXCEPTIONS as raven_exceptions

# Shared settings across prod, staging and simple

class Config(object):
    SENTRY_USER_ATTRS = ['email', 'name']
    PREFERRED_URL_SCHEME = 'https'
    OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 28800

    WTF_CSRF_CHECK_DEFAULT = True
    WTF_CSRF_ENABLED = True
    
    CACHE_TYPE = 'simple'

    RQ_DEFAULT_HOST = REDIS_HOST = CACHE_REDIS_HOST = \
        os.getenv('REDIS_HOST', 'redis-master')

    STORAGE_CONTAINER = os.environ.get('STORAGE_CONTAINER',  'ok-v3-user-files')

    RAVEN_IGNORE_EXCEPTIONS = raven_exceptions

    # Service Keys
    GOOGLE = {
        'consumer_key': os.environ.get('GOOGLE_ID'),
        'consumer_secret':  os.environ.get('GOOGLE_SECRET')
    }

    SENDGRID_AUTH = {
        'user': os.environ.get("SENDGRID_USER"),
        'key': os.environ.get("SENDGRID_KEY")
    }

    @classmethod
    def verify_oauth_credentials(cls):
        if "GOOGLE_ID" not in os.environ or "GOOGLE_SECRET" not in os.environ:
            print("Warning: the google login variables are not set.")
