""" Do not put secrets in this file. This file is public.
    Production config.
"""
import os

# Shared settings across all environments

def initialize_config(cls):
    cls.initialize_config()
    return cls

class Config(object):
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    DEBUG = False
    ASSETS_DEBUG = False
    TESTING_LOGIN = False
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_PORT = 6379
    RQ_POLL_INTERVAL = 2000
    RQ_DEFAULT_HOST = REDIS_HOST = \
        os.getenv('REDIS_HOST', 'localhost')

    STORAGE_SERVER = False
    STORAGE_PROVIDER = os.getenv('STORAGE_PROVIDER', 'LOCAL')
    STORAGE_CONTAINER = os.environ.get('STORAGE_CONTAINER', os.path.abspath("./local-storage"))
    STORAGE_KEY = os.environ.get('STORAGE_KEY', '')
    STORAGE_SECRET = os.environ.get('STORAGE_SECRET', '').replace('\\n', '\n')

    APPINSIGHTS_INSTRUMENTATIONKEY = os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY')

    @classmethod
    def initialize_config(cls):
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            if 'mysql' in db_url:
                db_url = db_url.replace('mysql://', 'mysql+pymysql://')
                db_url += "&sql_mode=STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION"

                #This defends against people copy/pasting a connection URL that doesn't include any query parameters 
                # (in which case the following code creates a bad URI)
                if '?' not in db_url:
                    db_url += '?'
        else:
            db_url = cls.get_default_db_url()

        cls.SQLALCHEMY_DATABASE_URI = db_url

        # If using sqlite use absolute path (otherwise we break migrations)
        sqlite_prefix = 'sqlite:///'
        if cls.SQLALCHEMY_DATABASE_URI.startswith(sqlite_prefix):
            cls.SQLALCHEMY_DATABASE_URI = (sqlite_prefix +
                    os.path.abspath(cls.SQLALCHEMY_DATABASE_URI[len(sqlite_prefix) + 1:]))

        if cls.STORAGE_PROVIDER == 'LOCAL' and not os.path.exists(cls.STORAGE_CONTAINER):
            os.makedirs(cls.STORAGE_CONTAINER)

        cls.verify_oauth_credentials()


    @classmethod
    def get_default_db_url(cls):
        raise NotImplementedError

    @classmethod
    def verify_oauth_credentials(cls):
        raise NotImplementedError
