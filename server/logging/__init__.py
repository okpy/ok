import logging

from flask import request
from flask_login import current_user

logger = logging.getLogger(__name__)

REQUEST_LOG_VARIABLE = 'okpy.log'

class RequestLog:
    def __init__(self):
        self.endpoint = request.url_rule and request.url_rule.endpoint
        self.lines = []

class RequestLogHandler(logging.Handler):
    """A log handler that attaches logs to the WSGI request environment."""
    def handle(self, record):
        try:
            request_log = request.environ[REQUEST_LOG_VARIABLE]
        except (RuntimeError, KeyError):
            # We're outside of a request context. This could happen if something
            # else tries to use a Python logger, like gunicorn or compiling
            # assets
            return
        request_log.lines.append(record)

def init_app(app):
    if app.debug:
        return

    if __name__ != '__main__':
        gunicorn_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_logger.handlers
        app.logger.setLevel(gunicorn_logger.level)

    root_logger = logging.getLogger()
    root_logger.setLevel(app.config['LOG_LEVEL'])
    root_logger.addHandler(RequestLogHandler())
    app.logger.propagate = True

    @app.before_request
    def start_request_log():
        request.environ[REQUEST_LOG_VARIABLE] = RequestLog()
