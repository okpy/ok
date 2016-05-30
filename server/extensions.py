from flask_cache import Cache
from flask_wtf.csrf import CsrfProtect
from flask_debugtoolbar import DebugToolbarExtension
from flask_assets import Environment

# Setup flask cache
cache = Cache()

csrf = CsrfProtect()

# init flask assets
assets_env = Environment()

debug_toolbar = DebugToolbarExtension()
