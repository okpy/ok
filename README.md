ok.py
=====

The ok.py server performs and displays analysis of student progress
based on logging sent from client scripts.

(Coming soon) Visit http://okpy.org to use our hosted service for your course.

The ok.py software was developed for CS 61A at UC Berkeley.

[![Build Status](https://travis-ci.org/Cal-CS-61A-Staff/ok.svg?branch=master)](https://travis-ci.org/Cal-CS-61A-Staff/ok)

Installation
-------------

Before installation, ensure that:
* The default Python installation is Python2.
  - To temporarily symlink the `python` command to Python2, run `rm /usr/bin/python; sudo ln -s /usr/bin/python2.7 /usr/bin/python`
* Ok directory's absolute path does *not* have spaces.
  - From your Ok directory, run `pwd` to see its full path.
  - In effect, the *installation* will not work in Google Drive or iCloud; the server may be subsequently run in the cloud.

To install:
* Clone this repo
* Install [Google App Engine SDK](https://developers.google.com/appengine/downloads) and add it to your `$PATH`. You can do `brew install google-app-engine` on a mac.
* `export GAE_SDK=<location of unzipped GAE SDK>`
  - For brew, this location should be in /usr/local/Cellar/google-app-engine/1.9.11/share/google-app-engine.
  - Some files that should be present when running `ls $GAE_SDK` are `dev_appserver.py` and `api_server.py`.
* Install `virtualenv`. You can do `brew install virtualenv` on a mac or `pip install virtualenv` or `apt-get install python-virtualenv`
  - If brew cannot find `virtualenv`, use `brew install pyenv-virtualenv`.
* Run `./install.py`. If you are running into trouble on this step, delete the `env` directory and rerun `./install.py`.
  - If install returns an Error and brew is installed, fix all issues under `brew doctor`.

Testing the Installation
------------------------
* Run `./run_tests`. For a successful installation, all tests should pass.

Starting the Server
-------------
```bash
$ cd server
$ ./start_server
```

Customizing seed content
-------------------
`app/seed/__init__.py` intializes the local dev appserver with sample content (Users, Assignments, a Course etc). You can customize it by changing the file and restarting the dev server.

Server Development
------------------

The server is developed in Python 2.7+ using the Google App Engine framework.

To start making changes to the server, first change to its virtual enviroment.

``source activate-server.sh``

In most environments, your prompt will change to start with ``(server)``.
To exit this environment, type ``deactivate``.

Core Features
-------------

TODO

Projects using ok.py
--------------------

TODO

Developer Guidelines
--------------------

TODO
