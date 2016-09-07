# Ok OAuth2

This document describes how to use the Ok OAuth Service.

OAuth Login will provide your service with a token that you can use to perform actions on the user's behalf.

For more information about OAuth2, refer to these documents: [OAuth2 Simplified](https://aaronparecki.com/2012/07/29/2/oauth2-simplified) & [GitHub's OAuth2 Documentation](https://developer.github.com/v3/oauth/)

<a href="https://ok-oauth.app.cs61a.org"><img src="https://cloud.githubusercontent.com/assets/882381/17834353/6ebacf94-66f1-11e6-8d3c-2b33a974383e.gif?cachebust" width="100%"></a>

[Demo of OK OAuth >](https://ok-oauth.app.cs61a.org)

> [Demo Source Code >](https://github.com/Cal-CS-61A-Staff/ok/blob/master/documentation/sample_oauth.py)

## Registering an OAuth Client
>> <h3>Demo App Redirect URIs</h3>
>> http://localhost:8000/authorized, http://127.0.0.1:8000/authorized, https://ok-oauth.app.cs61a.org/authorized, http://ok-oauth.app.cs61a.org/authorized


You can register an Ok OAuth Client from the Staff Dasbhoard. You will specify a client-id and be provided with a client secret.

This secret must be kept confidential. It may not be revealed publically (for example, listed in a public GitHub repository).

Your redirect URLs must be specified. The example application has these values set for valid redirect URI's. To change Ok OAuth app settings, contact us.

## Scopes

Scopes let you specify what level of access you need. Scopes limit access for OAuth tokens, they do not add permissions beyond what the user could already do.

Requested scopes will be displayed to the user on the authorize form.

The currently available scopes are `email` and `all`.

Scope | Description | Use for
----- | ----------- | ------
`email` | Access to user info & enrollment status. | Mainly for login capabilities
`all` | Access to all OK functionality | Need to submit assignments and view old submissions

To request multiple scopes, simply specify the scopes seperated by spaces.


## OAuth Client Configuration
Your requests should include a state nonce and a scope level.

### Development Config
When running locally, you can use the following settings for your OAuth2 Client.

Parameter | URL
---------- | -------
`base_url` | `http://localhost:5000/api/v3/`
`access_token_url` | `http://localhost:5000/oauth/token/`
`authorize_url` | `http://localhost:5000/oauth/authorize/`


### Production
When running in production, you can should the following settings for your OAuth2 Client.

Parameter | URL
---------- | -------
`base_url` | `https://okpy.org/api/v3/`
`access_token_url` | `https://okpy.org/oauth/token/`
`authorize_url` | `https://okpy.org/oauth/authorize/`


## Sample OK OAuth Client

A functional OAuth Login implementation is provided [in the OK repo](https://github.com/Cal-CS-61A-Staff/ok/blob/master/documentation/sample_oauth.py).
> [Example App Source Code >](https://github.com/Cal-CS-61A-Staff/ok/blob/master/documentation/sample_oauth.py)

If you are using Python & Flask OAuthLib an example config is provided here.

Most popular langauges provide an implementation of an OAuth2 client, it is reccomended to use those libraries if possible.

```python
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
