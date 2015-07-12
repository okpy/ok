ok.py
=====

The ok.py server performs and displays analysis of student progress
based on logging sent from client scripts.

(Coming soon) Visit http://okpy.org to use our hosted service for your course.

The ok.py software was developed for CS 61A at UC Berkeley.

[![Build Status](https://travis-ci.org/Cal-CS-61A-Staff/ok.svg?branch=master)](https://travis-ci.org/Cal-CS-61A-Staff/ok)
[![Coverage Status](https://coveralls.io/repos/Cal-CS-61A-Staff/ok/badge.svg?branch=master&service=github)](https://coveralls.io/github/Cal-CS-61A-Staff/ok?branch=master)

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
  - For brew, this location should be in /usr/local/Cellar/google-app-engine/1.9.X/share/google-app-engine.
  - Some files that should be present when running `ls $GAE_SDK` are `dev_appserver.py` and `api_server.py`.
* Install `virtualenv`. You can do `brew install virtualenv` on a mac or `pip install virtualenv` or `apt-get install python-virtualenv`
  - If brew cannot find `virtualenv`, use `brew install pyenv-virtualenv`.
* Run `./install.py`. If you are running into trouble on this step, delete the `env` directory and rerun `./install.py`.
  - If install returns an Error and brew is installed, fix all issues under `brew doctor`.

Testing the Installation
------------------------
* Run `./run_tests`. For a successful installation, all tests should pass.

Local Server
------------
To run the server locally:

```bash
$ source activate_server.sh 
$ bower install  # to install frontend CSS/JS libraries
$ ./start_server
```

Deploying
---------
To deploy the current branch:

```bash
$ bower install 
$ gcloud auth login
$ appcfg.py update
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

Backup Maintainence
- Best-effort maintenance of student backups that occur when ok is run.

Composition Grading
- Allow staff to comment on student composition of projects and assign grades.

Autograding
- Automatic grading of student submissions

Projects using ok.py
--------------------

[CS61A](cs61a.org) uses ok.py for all assignments.

Developer Guidelines
--------------------

To add features to ok, please do the following:

- Follow the Installation instructions in order to install the ok server.
- Name your branch according to our convention of &lt;category&gt;/&lt;GithubUsername&gt;/&lt;branch name&gt;
  * Category is one of the following things:
    - 'enhancement': This is a new feature that is being added to ok.
    - 'bug': This is when the purpose of the branch is to fix a bug in the current codebase.
    - 'cleanup': This is when technical debt is being reduced (e.g. adding tests, improving code style, etc)
  * Githubusername is the username of one person who is the point of contact for the branch. The point of contact should be the first person that will field questions about the branch- there might be many other people working on it.
  * branch name: A descriptive name for the branch
- Make a pull request, which will get code-reviewed and merged.

Some useful things for developers to know:

1. Testing with ok-client
   - To test with ok-client, please follow the instructions for the ok-client repo [here](https://github.com/Cal-CS-61A-Staff/ok-client).
   - Once you are inside the virtual environment for ok-client, you can make a new binary by using the command `ok-publish`.
   - To run the server, run the shell script in `server/start_server`
   - When running the ok binary, add the flags `--insecure --server localhost:<port>` to point it to the running ok-server
   - To find demo assignments that you can use the binary with, look in [ok-client/demo](https://github.com/Cal-CS-61A-Staff/ok-client/tree/master/demo)
