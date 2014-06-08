### Set up database
To set up the database, install mysql (`brew install mysql`).
Connect to the console as root, and run these commands:
`CREATE USER 'development'@'127.0.0.1' IDENTIFIED BY "develpp11pp";`
`GRANT ALL ON *.* TO 'development'@'%';

*Note: I know this isn't secure, but it's development.*

You should be able to look at the api and stuff now.