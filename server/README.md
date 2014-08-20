TODO Describe what's going on in the server.
Currently
=========
Permissions to CRUD are determined by the Model classes. Currently, the code requires the
actual object to be retrieved from the database before the permissions can be checked.


App Files
========
api.py
-------
- The API is a collection of resources based on respective models that each implement a GET/POST/DELETE
  - e.g. UserAPI corresponds to User model. GET/POST/DELETE work regularly, so no overrides
  - e.g. SubmitAPI has more involved process, so POST is overridden.

auth.py
-------
* Finds out who the user is (creates a model). 
  - Calls authenticator.py w/ access token. 
  - Creates a User model from email from oauth (in authenticator.py).

forms.py
--------

models.py
---------
Currently specifies:
* User, Assignment, Course, Submission models as per API Spec in Wiki (except Course).
* Each model has a can class method that checks for requirements (permissions).
  - This can class method requires the actual object from database before determining if permissions are granted.

permissions.py
--------------
* The permissions.py class is not used elsewhere in the code.

urls.py
-------
* Dispatches to different handlers based on URL.
* Currently: Processes /, 404, 500, API URLs
* Permissions are handled within API's Model objects themselves.
* Imported by `__init__.py`

views.py
--------
* Caches the app
* (Not supported yet): URL route handlers. Docstring is a bit misleading for now.

Infrastructure
==============
The OK server uses the following infrastructure defined in these locations:

    - Flask [app/]: web framework for URL routing, security, etc.
        - Jinja2 [app/templates]: Templating engine

    - Werkzeug [app/__init__.py]: a WSGI utility
        - [DebuggedApplication](http://werkzeug.pocoo.org/docs/debug/): middleware that enables interactive debugging with console

    - Mako [?]: ?

    - astroid [?]: ?

    - [flask-cache](https://github.com/thadeusb/flask-cache) [app/views.py]: Easy cache support (just pass app in to enable caching)

