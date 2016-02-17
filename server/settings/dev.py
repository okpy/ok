from server.settings import LocalConfig

class DevConfig(LocalConfig):
    ENV = 'dev'
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../development.db'
    RQ_LOW_URL = "redis://localhost:6379/1"

    CACHE_REDIS_URL = "redis://localhost:6379/0"
    CACHE_TYPE = 'simple'

    ASSETS_DEBUG = True
