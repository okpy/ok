CREATE DATABASE okpy;
FLUSH PRIVILEGES;
DELETE FROM mysql.user WHERE User = 'development';
CREATE USER 'development'@'localhost' IDENTIFIED BY "develpp11pp";
GRANT ALL ON *.* TO 'development'@'localhost';
