# Ok OAuth

This document describes how to use the Ok OAuth2 Service. OAuth Login will provide your service with a token that you can use to perform actions on the user's behalf.
For more information about OAuth2, refer to these [OAuth2 Simplified](https://aaronparecki.com/2012/07/29/2/oauth2-simplified) & [GitHub's OAuth2 Documentation](https://developer.github.com/v3/oauth/)

> [View Demo of OK OAuth >](https://ok-oauth.app.cs61a.org)
> [View Source Code for Example >](https://github.com/Cal-CS-61A-Staff/ok/blob/master/documentation/sample_oauth.py)

## Registering an OAuth Client

You can register an Ok OAuth Client from the Staff Dasbhoard. You will specify a client-id and be provided with a client secret. This secret must be kept confidential. It may not be revealed publically (for example, revealed on a public GitHub repository).

Your redirect URLs must be specified. The example application has these values set for valid redirect URI's
>> <h3>Sample Redirect URIs</h3>
> http://localhost:8000/authorized, http://127.0.0.1:8000/authorized, https://ok-oauth.app.cs61a.org/authorized, http://ok-oauth.app.cs61a.org/authorized

## OAuth Client Configuration

### Development

Parameter | Description | Value
---------- | ------- | -------
`base_url` | API Base URL | `http://localhost:5000/api/v3/`
`access_token_url` | Exchange a code for a token | `http://localhost:5000/oauth/token/`
`authorize_url` | Where to send users | `http://localhost:5000/oauth/authorize/`


### Production

Parameter | Description | Value
---------- | ------- | -------
`base_url` | API Base URL | `https://okpy.org/api/v3/`
`access_token_url` | Exchange a code for a token | `https://okpy.org/oauth/token/`
`authorize_url` | Where to send users | `https://okpy.org/oauth/authorize/`

Your requests should include a state nonce and a scope level.

## Scopes

Scopes let you specify what level of access you need. Scopes limit access for OAuth tokens, they do not add permissions beyond what the user could already do.

Requested scopes will be displayed to the user on the authorize form.

The currently available scopes are `email` and `all`.

> `email` Access to user info & enrollment status.
> `all` Access to all OK functionality (submit & view assignments)

To request multiple scopes, simply specify the scopes seperated by spaces.

## Sample OK OAuth Client
>><h4> Using Flask OAuthlib </h4>
```
from werkzeug import security
from flask_oauthlib.client import OAuth
oauth = OAuth(app)
remote = oauth.remote_app(
    'ok-server',  # Server Name
    consumer_key='example',
    consumer_secret='fake-secret-get-the-real-one',
    request_token_params={'scope': 'email',
                          'state': lambda: security.gen_salt(10)},
    base_url='https://okpy.org/api/v3/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://okpy.org/oauth/token',
    authorize_url='https://okpy.org/oauth/authorize'
)
```

A functional OAuth Login implementation is provided [in the OK repo](https://github.com/Cal-CS-61A-Staff/ok/blob/master/documentation/sample_oauth.py).

If you are using Python & Flask OAuthLib an example config is provided here.

Most popular langauges provide an implementation of an OAuth2 client, it is reccomended to use those libraries if possible.
