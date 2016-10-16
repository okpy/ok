from flask_cache import Cache
from flask_wtf.csrf import CsrfProtect
from flask_debugtoolbar import DebugToolbarExtension
from flask_assets import Environment
from flask_oauthlib.provider import OAuth2Provider

from raven.contrib.flask import Sentry

# Setup flask cache
cache = Cache()

csrf = CsrfProtect()

# oAuth Provider (not client)
oauth_provider = OAuth2Provider()

# init flask assets
assets_env = Environment()

debug_toolbar = DebugToolbarExtension()

# Sentry Error reporting
sentry = Sentry()
