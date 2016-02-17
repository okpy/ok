from server.settings.test import TestConfig

class SqliteConfig(TestConfig):
    ENV = 'sqlite'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../oksqlite.db'
    CACHE_TYPE = 'simple'