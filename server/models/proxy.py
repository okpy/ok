class ModelProxy(object):
    def __getattribute__(self, key):
        import server.models
        return server.models.__getattribute__(key)

ModelProxy = ModelProxy()
