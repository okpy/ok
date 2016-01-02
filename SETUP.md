OSX Postgres Setup:

$ brew install postgres
$ brew services postgres start
$ createuser -d postgres
$ createdb okdev -U postgres
