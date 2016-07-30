from flask_cache import Cache
from flask_wtf.csrf import CsrfProtect
from flask_debugtoolbar import DebugToolbarExtension
from flask_assets import Environment
from flask_kvsession import KVSessionExtension
from raven.contrib.flask import Sentry

# Setup flask cache
cache = Cache()

csrf = CsrfProtect()

# init flask assets
assets_env = Environment()

debug_toolbar = DebugToolbarExtension()

# Sentry Error reporting
sentry = Sentry()

# Server Side Sessions
kv_session = KVSessionExtension()