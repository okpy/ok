from app.utils import create_api_response

class Need(object):
    def __init__(self, action):
        self.action = action
        self.obj = None

    def set_object(self, obj):
        self.obj = obj

    def api_response(self):
        if self.obj:
            obj_name = (self.obj.__name__ if isinstance(self.obj, type) else
                        self.obj.__class__.__name__)
        else:
            obj_name = ""
        return create_api_response(
            400, "Don't have permission to {} {}".format(
                self.action, obj_name))


