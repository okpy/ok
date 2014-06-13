# vim: set ts=4 sw=4 et:
from io import BytesIO 
from functools import wraps
try:
    from urllib2 import addinfourl
    from httplib import HTTPMessage
except ImportError:
    from urllib.response import addinfourl
    from http.client import HTTPMessage
    basestring = str

from mock import patch


def with_patched_client(data, code=200, headers=None):
    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            with patch('sanction.urlopen') as mock_urlopen:
                bdata = type(data) is basestring and data.encode() or data
                sheaders = ''
                if headers is not None:
                    sheaders = '\r\n'.join(['{}: {}'.format(k, v) for k, v in
                        headers.items()])
                bheaders = (sheaders or '').encode()

                mock_urlopen.return_value = addinfourl(BytesIO(bdata), 
                    HTTPMessage(BytesIO(bheaders)), '', code=code)
                fn(*args, **kwargs)
        return inner
    return wrapper
