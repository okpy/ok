""" Do not put secrets in this file. This file is public.
    Production config.
"""
import os
import sys

from server.settings._base import Config as BaseConfig, initialize_config
from server.settings._prodbase import Config as ProdBaseConfig

@initialize_config
class Config(ProdBaseConfig, BaseConfig):
    ENV = 'prod'

    STORAGE_PROVIDER = os.environ.get('STORAGE_PROVIDER',  'GOOGLE_STORAGE')

    MAX_CONTENT_LENGTH = 30 * 1024 * 1024  # Max Upload Size is 30MB

    CACHE_TYPE = 'redis'
    CACHE_KEY_PREFIX = 'ok-web'

    # The Google Cloud load balancer behaves like two proxies:
    # one with the external fowarding rule IP, and
    # one with an internal IP.
    # See https://cloud.google.com/compute/docs/load-balancing/http/#target_proxies
    # Including Nginx too makes 3 proxies.
    NUM_PROXIES = 3

    @classmethod
    def get_default_db_url(cls):
        print("The database URL is not set!")
        sys.exit(1)

    @classmethod
    def get_default_redis_host(cls):
        return 'redis-master'

    @classmethod
    def get_flask_caching_enabled(cls):
        return True
