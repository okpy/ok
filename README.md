[![Logo](https://raw.githubusercontent.com/okpy/ok/master/server/static/img/logo-tiny.png)](#)
=====

The ok.py server collects submissions and displays analysis of student progress
based on logging sent from client scripts.

Courses can sign up for our free hosted service on [okpy.org](https://okpy.org)

The ok.py software was developed for CS 61A at UC Berkeley.

[![Build Status](https://circleci.com/gh/okpy/ok.svg?style=shield)](https://circleci.com/gh/okpy/ok)
[![Coverage Status](https://coveralls.io/repos/github/okpy/ok/badge.svg)](https://coveralls.io/github/okpy/ok)
[![Docker Repository on Quay](https://quay.io/repository/cs61a/ok-server/status "Docker Repository on Quay")](https://quay.io/repository/cs61a/ok-server)

View Documentation at [OK Documentation](https://okpy.github.io/documentation)

Installation
-------------

To install:
* Clone this repo
* Install `virtualenv`. You can do `brew install virtualenv` on a mac or `pip install virtualenv` or `apt-get install python-virtualenv`
  - If brew cannot find `virtualenv`, use `brew install pyenv-virtualenv`.
* Create a virtualenv with `virtualenv -p python3 env`
* Activate the virtualenv with `source env/bin/activate`
* (Optional, but recommended) Install `redis-server`. You can do `brew install redis` on a mac or `apt-get install redis-server`

Local Server
------------
To run the server locally:

```bash
$ source env/bin/activate # for virtualenv
$ pip install -r requirements.txt  # to install libraries
$ ./manage.py createdb
$ ./manage.py seed
$ ./manage.py server
```

The server will listen on http://localhost:5000.

If you are running into issues - see `documentation/SETUP.md` or file an issue

Running Workers
---------------
To run workers locally:

```bash
$ ./manage.py worker
```

To be able to run the workers you should have a `redis` server installed and running.

If `redis` is not installed you can install it using your distribution's package
manager or follow [Redis Quick Start](https://redis.io/topics/quickstart).

Command Line Manager
------------------------
* To view available commands run `./manage.py` once the virtualenv is activated.

Customizing seed content
-------------------
`server/generate.py` initializes the local server with sample content (Users, Assignments, a Course etc). You can customize it by changing the file and running `./manage.py resetdb`.

Server Development
------------------
The server is developed in Python 3.5+ using Flask.

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
- Many other UC Berkeley CS courses use ok.py

Developer Guidelines
--------------------
See `documentation/CONTRIBUTING.md`

Recent activity:

[![Throughput Graph](https://graphs.waffle.io/okpy/ok/throughput.svg)](https://waffle.io/okpy/ok/metrics/throughput)

Deploying
---------
Docker + Kubernetes on Google Container Engine. See `kubernetes/kubernetes.md` for more info.

The ok-server also supports deployments to Heroku or servers on any major hosting service.

There also exists a [one-click setup](./azure/paas/README.md) for ok-server on Azure.

Python Style Guide
-------------------
Refer to [The Elements of Python Style](https://github.com/amontalenti/elements-of-python-style)

Some useful things for developers to know:

1. Testing with ok-client
   - To test with ok-client, please follow the instructions for the ok-client repo [here](https://github.com/okpy/ok-client).
   - Once you are inside the virtual environment for ok-client, you can make a new binary by using the command `ok-publish`.
   - Start the local ok server.
   - When running the ok binary, add the flags `--insecure --server localhost:<port>` to point it to the running ok-server
   - To find demo assignments that you can use the binary with, look in [ok-client/demo](https://github.com/okpy/ok-client/tree/master/demo)
