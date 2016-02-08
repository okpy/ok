from hashids import Hashids
from urllib.parse import urlparse, urljoin

# ID hashing configuration.
# DO NOT CHANGE ONCE THE APP IS PUBLICLY AVAILABLE. You will break every
# link with an ID in it.
hashids = Hashids(min_length=6)

def encode_id(id_number):
    return hashids.encode(id_number)

def decode_id(value):
    numbers = hashids.decode(value)
    if len(numbers) != 1:
        raise ValueError('Could not decode hash {} into ID'.format(value))
    return numbers[0]

def local_time(dt, course):
    """Format a time string in a course's locale."""
    return course.timezone.localize(dt).strftime('%a %m/%d %H:%M %p')

def is_safe_redirect_url(request, target):
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ('http', 'https') and \
        host_url.netloc == redirect_url.netloc
