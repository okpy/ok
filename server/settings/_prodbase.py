import os
import sys

from server.settings import RAVEN_IGNORE_EXCEPTIONS as raven_exceptions

# Shared settings across prod, staging and simple

class Config(object):
    SENTRY_USER_ATTRS = ['email', 'name']
    PREFERRED_URL_SCHEME = 'https'
    OAUTH2_PROVIDER_TOKEN_EXPIRES_IN = 28800

    WTF_CSRF_CHECK_DEFAULT = True
    WTF_CSRF_ENABLED = True

    CACHE_TYPE = 'simple'

    STORAGE_CONTAINER = os.environ.get('STORAGE_CONTAINER',  'ok-v3-user-files')

    RAVEN_IGNORE_EXCEPTIONS = raven_exceptions

    SENDGRID_AUTH = {
        'user': os.environ.get("SENDGRID_USER"),
        'key': os.environ.get("SENDGRID_KEY")
    }

    if os.environ.get("GOOGLE_ID") and os.environ.get("GOOGLE_SECRET"):
        OAUTH_PROVIDER = 'GOOGLE'
    elif os.environ.get("MICROSOFT_APP_ID") and os.environ.get("MICROSOFT_APP_SECRET"):
        OAUTH_PROVIDER = 'MICROSOFT'
    else:
        print("Please set the Google or Microsoft OAuth ID and Secret variables.")
        sys.exit(1)
