from app.utils import create_api_response

class Need(object):
    def __init__(self, *needs):
        self.items = needs

    def make_api_error_message(self):
        return "Don't have permission to {}".format(' '.join(self.items))

class NeedException(Exception):
    def __init__(self, need, message=None):
        self.message = message
        self.need = need

    def __str__(self):
        return self.message or self.need.make_api_error_message()


