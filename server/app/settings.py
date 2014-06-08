"""
settings.py

Configuration for Flask app

Important: Place your keys in the secret_keys.py module,
           which should be kept out of version control.

"""

from app import secret_keys

class Config(object): #pylint: disable=R0903
    """
    Base config
    """
    # Set secret keys for CSRF protection
    SECRET_KEY = secret_keys.CSRF_SECRET_KEY
    CSRF_SESSION_KEY = secret_keys.SESSION_KEY
    # Flask-Cache settings
    CACHE_TYPE = 'gaememcached'
    SQLALCHEMY_DATABASE_URI = (
    '''mysql+mysqldb://development:develpp11pp@127.0.0.1/okpy''')

class Development(Config): #pylint: disable=R0903
    """
    Development config
    """
    DEBUG = True
    CSRF_ENABLED = True

class Testing(Config): #pylint: disable=R0903
    """
    Testing config
    """
    TESTING = True
    DEBUG = True
    CSRF_ENABLED = True

class Production(Config): #pylint: disable=R0903
    """
    Prod config
    """
    DEBUG = False
    CSRF_ENABLED = True
