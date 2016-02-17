from server.settings import LocalConfig

class TestConfig(LocalConfig):
    ENV = 'test'
    TESTING = True
