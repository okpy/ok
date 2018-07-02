import datetime
import json
import logging
import os
import traceback

import gcloud.logging
from google.protobuf.json_format import ParseDict
from google.protobuf.struct_pb2 import Struct
import gunicorn.glogging

from server.logging import REQUEST_LOG_VARIABLE

ACCESS_LOG_FORMAT = '%(message)s (%(pathname)s:%(lineno)d, in %(funcName)s)'
ERROR_LOG_FORMAT = '[gunicorn] %(message)s'

access_formatter = logging.Formatter(ACCESS_LOG_FORMAT)
error_formatter = logging.Formatter(ERROR_LOG_FORMAT)

def format_time(dt):
    """Formats a naive datetime as UTC time"""
    return dt.isoformat() + 'Z'

class ProcessCloudLogger:
    """Call get_logger() to get a Google Cloud logger instance. Ensures that
    each process has its own logger.
    """
    def __init__(self):
        self.logger_pid = None
        self.logger = None
        self.log_name = os.environ.get('GOOGLE_LOG_NAME', 'ok-default')

    def get_instance(self):
        pid = os.getpid()
        if self.logger_pid != pid:
            self.logger_pid = pid
            client = gcloud.logging.Client()
            self.logger = client.logger(self.log_name)
        return self.logger

    def log_proto(self, *args, **kwargs):
        try:
            self.get_instance().log_proto(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            traceback.print_exc()

    def log_struct(self, *args, **kwargs):
        try:
            self.get_instance().log_struct(*args, **kwargs)
        except Exception:
            traceback.print_exc()

    def log_text(self, *args, **kwargs):
        try:
            self.get_instance().log_text(*args, **kwargs)
        except Exception:
            traceback.print_exc()

class GoogleCloudHandler(logging.Handler):
    def __init__(self, cloud_logger):
        super().__init__()
        self.cloud_logger = cloud_logger

    def handle(self, record):
        message = error_formatter.format(record)
        self.cloud_logger.log_text(message, severity=record.levelname)

class Logger(gunicorn.glogging.Logger):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cloud_logger = ProcessCloudLogger()
        self.error_log.addHandler(GoogleCloudHandler(self.cloud_logger))

    def access(self, resp, req, environ, request_time):
        super().access(resp, req, environ, request_time)

        # Ignore health check
        if environ['PATH_INFO'] == '/healthz':
            return

        # See gunicorn/glogging.py
        status = resp.status
        if isinstance(status, str):
            status = status.split(None, 1)[0]
        now = datetime.datetime.utcnow()

        level = logging.NOTSET
        message = {
            '@type': 'type.googleapis.com/google.appengine.logging.v1.RequestLog',
            'ip': environ.get('REMOTE_ADDR'),
            'startTime': format_time(now - request_time),
            'endTime': format_time(now),
            'latency': '%d.%06ds' % (request_time.seconds, request_time.microseconds),
            'method': environ['REQUEST_METHOD'],
            'resource': environ['PATH_INFO'],
            'httpVersion': environ['SERVER_PROTOCOL'],
            'status': status,
            'responseSize': getattr(resp, 'sent', None),
            'userAgent': environ.get('HTTP_USER_AGENT'),
        }

        request_log = environ.get(REQUEST_LOG_VARIABLE)
        if request_log:
            message['urlMapEntry'] = request_log.endpoint
            message['line'] = [
                {
                    'time': format_time(datetime.datetime.utcfromtimestamp(record.created)),
                    'severity': record.levelname,
                    'logMessage': access_formatter.format(record),
                    # The log viewer only wants real App Engine files, so we
                    # can't put the actual file here.
                    'sourceLocation': None,
                }
                for record in request_log.lines
            ]
            level = max(
                (record.levelno for record in request_log.lines),
                default=logging.NOTSET,
            )

        if level > logging.NOTSET:
            severity = logging.getLevelName(level)
        else:
            severity = None

        struct_pb = ParseDict(message, Struct())
        self.cloud_logger.log_proto(struct_pb, severity=severity)


if os.getenv('APPINSIGHTS_INSTRUMENTATIONKEY'):
    Logger = gunicorn.glogging.Logger
