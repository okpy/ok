from app.utils import create_api_response

class Need(object):
    def __init__(self, *needs):
        self.items = needs

    def make_api_error(self):
        return create_api_response(
                401, "Don't have permission to {}".format(' '.join(self.items)))
