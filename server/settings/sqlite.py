from server.settings import LocalConfig

class SqliteConfig(LocalConfig):
    ENV = 'sqlite'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///../oksqlite.db'
    CACHE_TYPE = 'simple'
