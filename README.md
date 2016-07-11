ok.py
=====

The ok.py server collects submissions and displays analysis of student progress
based on logging sent from client scripts.

Contact us to use our hosted service (http://okpy.org) for your course.

The ok.py software was developed for CS 61A at UC Berkeley.

[![Build Status](https://travis-ci.org/Cal-CS-61A-Staff/ok.svg?branch=master)](https://travis-ci.org/Cal-CS-61A-Staff/ok)
[![Coverage Status](https://coveralls.io/repos/github/Cal-CS-61A-Staff/ok/badge.svg?branch=master)](https://coveralls.io/github/Cal-CS-61A-Staff/ok?branch=master)

View Documentation at [OK Documentation](https://okpy.github.io/documentation)

Installation
-------------

To install:
* Clone this repo
* Install `virtualenv`. You can do `brew install virtualenv` on a mac or `pip install virtualenv` or `apt-get install python-virtualenv`
  - If brew cannot find `virtualenv`, use `brew install pyenv-virtualenv`.
* Create a virtualenv with `virtualenv -p python3 env`
* Activate the virtualenv with `source env/bin/activate`

Local Server
------------
To run the server locally:

```bash
$ source env/bin/activate
$ pip install -r requirements.txt  # to install libraries
$ ./manage.py createdb
$ ./manage.py seed
$ ./manage.py server
```

The server will listen on http://localhost:5000.

Command Line Manager
------------------------
* To view available commands run `./manage.py` once the virtualenv is activated.

Customizing seed content
-------------------
`server/generate.py` intializes the local server with sample content (Users, Assignments, a Course etc). You can customize it by changing the file and running `./manage.py resetdb`.

Server Development
------------------
The server is developed in Python 3.4+ using Flask.

Core Features
-------------

Backup Maintenance
- Best-effort maintenance of student backups that occur when ok is run.

Composition Grading
- Allow staff to comment on student composition of projects and assign grades.

Autograding
- Automatic grading of student submissions

Projects using ok.py
--------------------
- [CS61A](http://cs61a.org) uses ok.py for all assignments.
- 3 other UC Berkeley CS courses use ok.py

Developer Guidelines
--------------------
See `documentation/CONTRIBUTING.md`

Deploying
---------
[![Docker Repository on Quay](https://quay.io/repository/cs61a/ok-server/status "Docker Repository on Quay")](https://quay.io/repository/cs61a/ok-server)

Docker + Kubernetes on Google Container Engine. See `kubernetes/kubernetes.md` for more info.

The ok-server also supports deployments to Heroku or servers on any major hosting service.

Python Style Guide
-------------------
Refer to [The Elements of Python Style](https://github.com/amontalenti/elements-of-python-style)

Some useful things for developers to know:

1. Testing with ok-client
   - To test with ok-client, please follow the instructions for the ok-client repo [here](https://github.com/Cal-CS-61A-Staff/ok-client).
   - Once you are inside the virtual environment for ok-client, you can make a new binary by using the command `ok-publish`.
   - Start the local ok server.
   - When running the ok binary, add the flags `--insecure --server localhost:<port>` to point it to the running ok-server
   - To find demo assignments that you can use the binary with, look in [ok-client/demo](https://github.com/Cal-CS-61A-Staff/ok-client/tree/master/demo)
