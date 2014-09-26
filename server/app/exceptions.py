class APIException(Exception):
    code = 400


class BadValueError(APIException):
    code = 400


class BadMethodError(APIException):
    code = 405


class IncorrectHTTPMethodError(APIException):
    code = 405


class PermissionError(APIException):
    code = 401

    def __init__(self, need):
        self.need = need

    @property
    def message(self):
        return self.need.get_exception_message()


class BadKeyError(APIException):
    code = 404

    def __init__(self, key):
        self.key = key

    @property
    def message(self):
        return "Key {key} not found".format(key=self.key)


class IncorrectVersionError(APIException):
    code = 403
