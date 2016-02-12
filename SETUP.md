App Setup:

$ make env

OR:

$ pip install virtualenv
$ virtualenv env
$ source env/bin/activate
$ pip install -r requirements.txt

Database Setup:

$ brew install mysql  # or similar for your machine
$ mysql.server start
$ mysql -u root < setup.sql

Create a seed database:

$ ./manage.py createdb
$ ./manage.py seed

Running App:

$ ./manage.py server

Open http://localhost:5000 in your browser of choice.

Settings:

$ cp server/settings/prod.sample.py server/settings/prod.py
