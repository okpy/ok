class APIException(Exception):
    code = 400


class BadValueError(APIException):
    code = 400


class BadArgumentException(APIException):
    code = 400


class BadMethodError(APIException):
    code = 400


class IncorrectHTTPMethodError(APIException):
    code = 400


class PermissionError(APIException):
    code = 401

    def __init__(self, need):
        self.need = need

    @property
    def message(self):
        return self.need.get_exception_message()


class ResourceDoesntExistError(APIException):
    code = 404


class IncorrectVersionError(APIException):
    code = 400
