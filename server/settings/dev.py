from server.settings import LocalConfig

class DevConfig(LocalConfig):
    ENV = 'dev'
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../database.db'

    CACHE_TYPE = 'simple'
    ASSETS_DEBUG = True
