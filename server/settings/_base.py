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

    STORAGE_SERVER = False
    STORAGE_PROVIDER = os.getenv('STORAGE_PROVIDER', 'LOCAL')
    STORAGE_CONTAINER = os.environ.get('STORAGE_CONTAINER', os.path.abspath("./local-storage"))
    STORAGE_KEY = os.environ.get('STORAGE_KEY', '')
    STORAGE_SECRET = os.environ.get('STORAGE_SECRET', '').replace('\\n', '\n')

    APPINSIGHTS_INSTRUMENTATIONKEY = os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY')
    
    # Service Keys
    GOOGLE = dict(
        consumer_key=os.environ.get('GOOGLE_ID'),
        consumer_secret=os.environ.get('GOOGLE_SECRET'),
        base_url='https://www.googleapis.com/oauth2/v3/',
        access_token_url='https://accounts.google.com/o/oauth2/token',
        authorize_url='https://accounts.google.com/o/oauth2/auth',
        profile_url="https://www.googleapis.com/plus/v1/people/me?access_token={}",
        userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo?access_token={}",
        request_token_params={
            'scope': 'email',
            'prompt': 'select_account'
        },
        request_token_url=None,
        access_token_method='POST'
    )

    # Don't use 'common' as the AAD Endpoint as that will allow MSA, and non guest users to logon
    # when Tenant is set to the AAD Tenant name, this restricts users and guest users
    MICROSOFT = dict(
        consumer_key=os.environ.get('MICROSOFT_APP_ID'),
        consumer_secret=os.environ.get('MICROSOFT_APP_SECRET'),
        tenent_id=os.environ.get('MICROSOFT_TENANT_ID'),
        base_url='https://graph.microsoft.com/v1.0/',
        request_token_url=None,
        access_token_method='POST',
        access_token_url='https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token' \
            .format(tenant_id=os.environ.get('MICROSOFT_TENANT_ID')),
        authorize_url='https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize' \
            .format(tenant_id=os.environ.get('MICROSOFT_TENANT_ID')),
        request_token_params={'scope': 'offline_access User.Read'}
    )

    @classmethod
    def initialize_config(cls):

        cls.configure_redis()

        db_url = os.getenv('DATABASE_URL')
        if db_url:
            if 'mysql' in db_url:
                db_url = db_url.replace('mysql://', 'mysql+pymysql://')

                # This defends against people copy/pasting a connection URL that doesn't include any query parameters
                # (in which case the following code creates a bad URI)
                if '?' not in db_url:
                    db_url += '?'

                db_url += "&sql_mode=STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION"
        else:
            db_url = cls.get_default_db_url()

        cls.SQLALCHEMY_DATABASE_URI = db_url

        # If using sqlite use absolute path (otherwise we break migrations)
        sqlite_prefix = 'sqlite:///'
        if cls.SQLALCHEMY_DATABASE_URI.startswith(sqlite_prefix):
            cls.SQLALCHEMY_DATABASE_URI = (sqlite_prefix +
                    os.path.abspath(cls.SQLALCHEMY_DATABASE_URI[len(sqlite_prefix) + 1:]))

        sql_ca_cert = os.getenv('SQL_CA_CERT', os.path.abspath('./BaltimoreCyberTrustRoot.crt.pem'))
        if sql_ca_cert and 'azure' in cls.SQLALCHEMY_DATABASE_URI:
            cls.SQLALCHEMY_ENGINE_OPTS = {'connect_args': {'ssl': {'ca': sql_ca_cert}}, 'pool_pre_ping': True}

        if cls.STORAGE_PROVIDER == 'LOCAL' and not os.path.exists(cls.STORAGE_CONTAINER):
            os.makedirs(cls.STORAGE_CONTAINER)


    @classmethod
    def get_default_db_url(cls):
        raise NotImplementedError

    @classmethod
    def verify_oauth_credentials(cls):
        raise NotImplementedError

    @classmethod
    def configure_redis(cls):
        ''' Configures Redis by inspecting the environment
        and setting Config properties'''

        # use REDIS_URL in preference to other Redis configuration
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            cls.REDIS_URL = redis_url
            cls.RQ_DEFAULT_URL = redis_url
            if cls.get_flask_caching_enabled():
                cls.CACHE_REDIS_URL = redis_url

        else:
            cls.REDIS_PORT = int(os.getenv('REDIS_PORT', "6379"))
            cls.REDIS_HOST = os.getenv('REDIS_HOST', cls.get_default_redis_host())

            # setup Redis config for RQ
            cls.RQ_DEFAULT_HOST = cls.REDIS_HOST

            # setup Redis config for Flash-Cache
            if cls.get_flask_caching_enabled():
                cls.CACHE_REDIS_HOST = cls.REDIS_HOST

        cls.RQ_POLL_INTERVAL = 2000

    @classmethod
    def get_default_redis_host(cls):
        ''' Returns the default Redis host.
        Overridden in specific environment settings'''
        return 'localhost'

    @classmethod
    def get_flask_caching_enabled(cls):
        ''' Returns True if flask caching should be enabled
        Overridden in specific environment settings'''
        return False