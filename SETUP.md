App Setup:

$ make env

OR:

$ pip install virtualenv
$ virtualenv env
$ source env/bin/activate
$ pip install -r requirements.txt

OSX Postgres Setup:

$ brew install postgres
$ brew services start postgres
$ createuser -d postgres
$ createdb okdev -U postgres

DB Setup:

$ ./manage.py createdb
$ ./manage.py seed

Running App:

$ ./manage.py runserver

Open http://localhost:5000 in your browser of choice.
