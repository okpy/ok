TODO Merge with ../README.md

Permissions
===========
Permissions to Create, Read, Update, and Delete records are determined by the
Model classes. Each ``Model`` class has a ``can`` method that receives a
``User`` instance, a declared ``Need``, and optionally the object being
accessed. This object must be retrieved from the database before the
permissions can be checked.

See https://github.com/Cal-CS-61A-Staff/ok/wiki/Permissions

App Files
========

api.py
------
The API describes resources for each model, including the effect of GET,
POST, and DELETE HTTP requests.

- e.g. ``UserAPI`` corresponds to ``User`` model. GET/POST/DELETE work
  regularly, so the generic ``APIResource`` generates responses.
- e.g. ``SubmitAPI`` has more involved process, so POST is overridden.

auth.py
-------
Maps authorization credentials to ``User`` instances.

- Calls ``authenticator.authenticate`` with an access token.
- Gets or creates a ``User`` instance from an email address.

forms.py
--------

models.py
---------
Implements the models described on the Wiki.

https://github.com/Cal-CS-61A-Staff/ok/wiki/Models

urls.py
-------
Dispatches to different handlers based on URL.
- Currently: Processes /, 404, 500, API URLs
- Permissions are handled within API's Model objects themselves.
- Imported by `__init__.py`

views.py
--------
(Not supported yet) URL route handlers.
- Also caches the app.

Infrastructure
==============
The OK server uses the following infrastructure defined in these locations:

- Flask [app/]: web framework for URL routing, security, etc.
  - Jinja2 [app/templates]: Templating engine

- Werkzeug [app/__init__.py]: a WSGI utility
    - [DebuggedApplication](http://werkzeug.pocoo.org/docs/debug/): middleware that enables interactive debugging with console

- [flask-cache](https://github.com/thadeusb/flask-cache) [app/views.py]: Easy cache support (just pass app in to enable caching)

