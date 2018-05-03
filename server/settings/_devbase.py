# Shared settings across dev and test

class Config(object):
    ASSETS_DEBUG = True
    TESTING_LOGIN = True
    INSTANTCLICK = True

    CACHE_TYPE = 'simple'

    GOOGLE_CONSUMER_KEY = ''

    @classmethod
    def verify_oauth_credentials(cls):
        pass
