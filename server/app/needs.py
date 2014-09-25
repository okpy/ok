from app.utils import create_api_response

class Need(object):
    """A need represents an action taken on an object, such as getting it."""

    def __init__(self, action):
        self.action = action
        self.obj = None

    def set_object(self, obj):
        self.obj = obj

    def get_exception_message(self):
        class_name = ""
        if isinstance(self.obj, type):
            class_name = self.obj.__name__
        elif self.obj:
            class_name = type(self.obj).__name__
        return "Don't have permission to {} {}".format(
            self.action, class_name)
