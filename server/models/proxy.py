class ModelProxy(object):
    def __getattribute__(self, key):
        import server.models.model
        return server.models.model.__getattribute__(key)

ModelProxy = ModelProxy()
