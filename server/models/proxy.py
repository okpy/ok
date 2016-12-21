import server.models.model

class ModelProxy(object):
    def __getattribute__(self, key):
        module = server.models.model.__getattribute__(key)
        return module.__getattribute__(key)

ModelProxy = ModelProxy()
