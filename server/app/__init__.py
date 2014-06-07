"""
Initialize Flask app

"""
from flask import Flask
import os
from werkzeug.debug import DebuggedApplication

app = Flask('app')

if os.getenv('FLASK_CONF') == 'DEV':
	#development settings n
    app.config.from_object('app.settings.Development')

    # Google app engine mini profiler
    # https://github.com/kamens/gae_mini_profiler
    app.wsgi_app = DebuggedApplication(app.wsgi_app, evalex=True)
elif os.getenv('FLASK_CONF') == 'TEST':
    app.config.from_object('app.settings.Testing')

else:
    app.config.from_object('app.settings.Production')

# Enable jinja2 loop controls extension
app.jinja_env.add_extension('jinja2.ext.loopcontrols')

# Pull in URL dispatch routes
import urls