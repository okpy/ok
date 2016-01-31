from hashids import Hashids
from werkzeug.routing import BaseConverter, ValidationError
from urllib.parse import urlparse, urljoin

from server.extensions import cache

class HashidConverter(BaseConverter):
    # ID hashing configuration.
    # DO NOT CHANGE ONCE THE APP IS PUBLICLY AVAILABLE. You will break every
    # link with an ID in it.
    hashids = Hashids(min_length=6)

    def to_python(self, value):
        numbers = self.hashids.decode(value)
        if len(numbers) != 1:
            raise ValidationError('Could not decode hash {} into ID'.format(value))
        return numbers[0]

    def to_url(self, value):
        return self.hashids.encode(value)

def is_safe_redirect_url(request, target):
  host_url = urlparse(request.host_url)
  redirect_url = urlparse(urljoin(request.host_url, target))
  return redirect_url.scheme in ('http', 'https') and \
    host_url.netloc == redirect_url.netloc
