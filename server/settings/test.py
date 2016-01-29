from server.settings import LocalConfig

class TestConfig(LocalConfig):
    ENV = 'test'
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../testing.db'

    CACHE_TYPE = 'null'
    WTF_CSRF_ENABLED = False
