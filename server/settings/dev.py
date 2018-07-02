import os

from server.settings._base import Config as BaseConfig, initialize_config
from server.settings._devbase import Config as DevBaseConfig

@initialize_config
class Config(DevBaseConfig, BaseConfig):
    ENV = 'dev'

    SECRET_KEY = os.getenv('OK_SESSION_KEY', 'changeinproductionkey')

    INSTANTCLICK = True

    DEBUG = True

    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # Max Upload Size is 20MB

    @classmethod
    def get_default_db_url(cls):
        return 'sqlite:///../oksqlite.db'
