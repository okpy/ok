App Setup:

$ make env

OR:

$ pip install virtualenv
$ virtualenv env
$ source env/bin/activate
$ pip install -r requirements.txt

DB Setup:

$ mysql - u root
> create user okdev;
> create database IF NOT EXISTS oktest;
> create database IF NOT EXISTS okdev;
> CREATE USER 'okdev'@'localhost' IDENTIFIED BY '';
> GRANT ALL PRIVILEGES ON oktest . * TO 'okdev'@'localhost'; FLUSH PRIVILEGES;
> GRANT ALL PRIVILEGES ON okdev . * TO 'okdev'@'localhost'; FLUSH PRIVILEGES;

$ ./manage.py createdb
$ ./manage.py seed

Running App:

$ ./manage.py server

Open http://localhost:5000 in your browser of choice.

Settings:

$ cp server/settings/prod.sample.py server/settings/prod.py
