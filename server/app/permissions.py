"""Permissions system"""

#pylint: disable=too-few-public-methods

class Permission(object):
    """Base permissions object"""
    def __init__(self, obj):
        self._obj = obj

    def get_message(self):
        return "No permission to access " + str(self._obj.__class__.__name__)



