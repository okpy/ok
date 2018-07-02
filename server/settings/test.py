import os

from server.settings._base import Config as BaseConfig, initialize_config
from server.settings._devbase import Config as DevBaseConfig

@initialize_config
class Config(DevBaseConfig, BaseConfig):
    ENV = 'test'

    SECRET_KEY = os.getenv('OK_SESSION_KEY', 'testkey')

    WTF_CSRF_CHECK_DEFAULT = False
    WTF_CSRF_ENABLED = False
    RQ_DEFAULT_DB = 2  # to prevent conflicts with development

    APPINSIGHTS_INSTRUMENTATIONKEY = ''

    @classmethod
    def get_default_db_url(cls):
        return os.getenv('SQLALCHEMY_URL', 'sqlite:///../oktest.db')
