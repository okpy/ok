from werkzeug.exceptions import (Forbidden, NotFound, Unauthorized,
                                 ClientDisconnected, MethodNotAllowed)

RAVEN_IGNORE_EXCEPTIONS = [Forbidden, NotFound, Unauthorized,
                           ClientDisconnected, MethodNotAllowed]
