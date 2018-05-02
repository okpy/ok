""" Do not put secrets in this file. This file is public.
    Production config.
"""
import os

from server.settings._base import Config as BaseConfig, initialize_config
from server.settings._prodbase import Config as ProdBaseConfig

@initialize_config
class Config(ProdBaseConfig, BaseConfig):
    ENV = 'simple'

    PREFERRED_URL_SCHEME = 'http'

    RQ_DEFAULT_HOST = REDIS_HOST = CACHE_REDIS_HOST = \
        os.getenv('REDIS_HOST', 'localhost')

    @classmethod
    def get_default_db_url(cls):
        return os.getenv('SQLALCHEMY_URL', 'sqlite:///../oksqlite.db')
