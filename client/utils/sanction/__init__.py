# vim: set ts=4 sw=)

from functools import wraps
from json import loads
from datetime import datetime, timedelta
from time import mktime
try:
    from urllib import urlencode
    from urllib2 import Request, urlopen
    from urlparse import urlsplit, urlunsplit, parse_qsl

    # monkeypatch httpmessage
    from httplib import HTTPMessage
    def get_charset(self):
        try:
            data = filter(lambda s: 'Content-Type' in s, self.headers)[0]
            if 'charset' in data:
                cs = data[data.index(';') + 1:-2].split('=')[1].lower()
                return cs
        except IndexError:
            pass

        return 'utf-8'
    HTTPMessage.get_content_charset = get_charset 
except ImportError: # pragma: no cover
    from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl
    from urllib.request import Request, urlopen


class Client(object):
    """ OAuth 2.0 client object
    """

    def __init__(self, auth_endpoint=None, token_endpoint=None,
        resource_endpoint=None, client_id=None, client_secret=None,
        token_transport=None):
        """ Instantiates a `Client` to authorize and authenticate a user

        :param auth_endpoint: The authorization endpoint as issued by the
                              provider. This is where the user should be
                              redirect to provider authorization for your
                              application.
        :param token_endpoint: The endpoint against which a `code` will be
                               exchanged for an access token.
        :param resource_endpoint: The base url to use when accessing resources
                                  via `Client.request`.
        :param client_id: The client ID as issued by the provider.
        :param client_secret: The client secret as issued by the provider. This
                              must not be shared.
        """
        assert token_transport is None or hasattr(token_transport, '__call__')

        self.auth_endpoint = auth_endpoint
        self.token_endpoint = token_endpoint
        self.resource_endpoint = resource_endpoint
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.token_transport = token_transport or transport_query
        self.token_expires = -1
        self.refresh_token = None

    def auth_uri(self, redirect_uri=None, scope=None, scope_delim=None, 
        state=None, **kwargs):

        """  Builds the auth URI for the authorization endpoint

        :param scope: (optional) The `scope` parameter to pass for
                      authorization. The format should match that expected by
                      the provider (i.e. Facebook expects comma-delimited,
                      while Google expects space-delimited)
        :param state: (optional) The `state` parameter to pass for
                      authorization. If the provider follows the OAuth 2.0
                      spec, this will be returned to your `redirect_uri` after
                      authorization. Generally used for CSRF protection.
        :param **kwargs: Any other querystring parameters to be passed to the
                         provider.
        """
        kwargs.update({
            'client_id': self.client_id,
            'response_type': 'code',
        })

        if scope is not None:
            kwargs['scope'] = scope

        if state is not None:
            kwargs['state'] = state

        if redirect_uri is not None:
            kwargs['redirect_uri'] = redirect_uri

        return '%s?%s' % (self.auth_endpoint, urlencode(kwargs))

    def request_token(self, parser=None, redirect_uri=None, **kwargs):
        """ Request an access token from the token endpoint.
        This is largely a helper method and expects the client code to
        understand what the server expects. Anything that's passed into
        ``**kwargs`` will be sent (``urlencode``d) to the endpoint. Client
        secret and client ID are automatically included, so are not required
        as kwargs. For example::

            # if requesting access token from auth flow:
            {
                'code': rval_from_auth,
            }

            # if refreshing access token:
            {
                'refresh_token': stored_refresh_token,
                'grant_type': 'refresh_token',
            }

        :param parser: Callback to deal with returned data. Not all providers
                       use JSON.
        """
        kwargs = kwargs and kwargs or {}

        parser = parser or _default_parser
        kwargs.update({
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'grant_type' in kwargs and kwargs['grant_type'] or \
                'authorization_code'
        })
        if redirect_uri is not None:
            kwargs.update({'redirect_uri': redirect_uri})

        # TODO: maybe raise an exception here if status code isn't 200?
        msg = urlopen(self.token_endpoint, urlencode(kwargs).encode(
            'utf-8'))
        data = parser(msg.read().decode(msg.info().get_content_charset() or
            'utf-8'))

        for key in data:
            setattr(self, key, data[key])

        # expires_in is RFC-compliant. if anything else is used by the
        # provider, token_expires must be set manually
        if hasattr(self, 'expires_in'):
            try:
                # python3 dosn't support long
                seconds = long(self.expires_in)
            except:
                seconds = int(self.expires_in)
            self.token_expires = mktime((datetime.utcnow() + timedelta(
                seconds=seconds)).timetuple())

    def refresh(self):
        self.request_token(refresh_token=self.refresh_token,
            grant_type='refresh_token')

    def request(self, url, method=None, data=None, headers=None, parser=None): 
        """ Request user data from the resource endpoint
        :param url: The path to the resource and querystring if required
        :param method: HTTP method. Defaults to ``GET`` unless data is not None
                       in which case it defaults to ``POST``
        :param data: Data to be POSTed to the resource endpoint
        :param parser: Parser callback to deal with the returned data. Defaults
                       to ``json.loads`.`
        """
        assert self.access_token is not None
        parser = parser or loads 

        if not method:
            method = 'GET' if not data else 'POST'

        req = self.token_transport('{0}{1}'.format(self.resource_endpoint, 
            url), self.access_token, data=data, method=method, headers=headers)

        resp = urlopen(req)
        data = resp.read()
        try:
            return parser(data.decode(resp.info().get_content_charset() or
                'utf-8'))
            # try to decode it first using either the content charset, falling
            # back to utf-8

        except UnicodeDecodeError:
            # if we've gotten a decoder error, the calling code better know how
            # to deal with it. some providers (i.e. stackexchange) like to gzip
            # their responses, so this allows the client code to handle it
            # directly.
            return parser(data)


def transport_headers(url, access_token, data=None, method=None, headers=None):
    try:
        req = Request(url, data=data, method=method)
    except TypeError:
        req = Request(url, data=data)
        req.get_method = lambda: method

    add_headers = {'Authorization': 'Bearer {0}'.format(access_token)}
    if headers is not None:
        add_headers.update(headers)

    req.headers.update(add_headers)
    return req


def transport_query(url, access_token, data=None, method=None, headers=None):
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query))
    query.update({
        'access_token': access_token
    })
    url = urlunsplit((parts.scheme, parts.netloc, parts.path,
        urlencode(query), parts.fragment))
    try:
        req = Request(url, data=data, method=method)
    except TypeError:
        req = Request(url, data=data)
        req.get_method = lambda: method

    if headers is not None:
        req.headers.update(headers)

    return req


def _default_parser(data):
    try:
        return loads(data)
    except ValueError:
        return dict(parse_qsl(data))
