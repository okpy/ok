""" Do not put secrets in this file. This file is public.
    For staging environment (Using Dokku)
"""
import os

from server.settings._base import Config as BaseConfig, initialize_config
from server.settings._prodbase import Config as ProdBaseConfig

@initialize_config
class Config(ProdBaseConfig, BaseConfig):
    ENV = 'staging'

    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # Max Upload Size is 10MB

    STORAGE_CONTAINER = os.environ.get('STORAGE_CONTAINER', os.path.abspath("./local-storage"))

    @classmethod
    def get_default_db_url(cls):
        return os.getenv('SQLALCHEMY_URL', 'sqlite:///../oksqlite.db')
