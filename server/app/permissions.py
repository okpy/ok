"""Permissions system"""

#pylint: disable=too-few-public-methods

class Permission(object):
    """Base permissions object"""
    def __init__(self, obj):
        self._obj = obj

    def __str__(self):
        return "Permission"



