from server.settings import LocalConfig

class DevConfig(LocalConfig):
    ENV = 'dev'
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost:5432/okdev'

    CACHE_TYPE = 'simple'
    ASSETS_DEBUG = True
