from server.settings import LocalConfig

class TestConfig(LocalConfig):
    ENV = 'test'
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:@localhost:5432/oktest'

    CACHE_TYPE = 'simple'
    WTF_CSRF_ENABLED = False
