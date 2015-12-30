OSX Postgres Setup:

$ brew install postgres
$ brew services postgres start
$ createuser -d okdev
$ createdb okdev -U okdev
