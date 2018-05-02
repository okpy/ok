import os

# Shared settings across prod, staging and simple

class Config(object):
    SENTRY_USER_ATTRS = ['email', 'name']
    PREFERRED_URL_SCHEME = 'https'
    OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 28800

    WTF_CSRF_CHECK_DEFAULT = True
    WTF_CSRF_ENABLED = True
    
    CACHE_TYPE = 'simple'
    CACHE_KEY_PREFIX = 'ok-web'

    RQ_DEFAULT_HOST = REDIS_HOST = CACHE_REDIS_HOST = \
        os.getenv('REDIS_HOST', 'redis-master')

    STORAGE_CONTAINER = os.environ.get('STORAGE_CONTAINER',  'ok-v3-user-files')

    @classmethod
    def verify_oauth_credentials(cls):
        if "GOOGLE_ID" not in os.environ or "GOOGLE_SECRET" not in os.environ:
            print("Warning: the google login variables are not set.")
