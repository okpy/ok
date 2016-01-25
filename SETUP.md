App Setup:

$ make env

OR:

$ pip install virtualenv
$ virtualenv env
$ source env/bin/activate
$ pip install -r requirements.txt

DB Setup:

$ ./manage.py createdb
$ ./manage.py seed

Running App:

$ ./manage.py server

Open http://localhost:5000 in your browser of choice.

Settings:

$ cp server/settings/prod.sample.py server/settings/prod.py
