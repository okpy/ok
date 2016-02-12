CREATE USER IF NOT EXISTS 'okdev'@'localhost';
CREATE DATABASE IF NOT EXISTS okdev;
CREATE DATABASE IF NOT EXISTS oktest;
GRANT ALL PRIVILEGES ON okdev.* TO 'okdev'@'localhost';
GRANT ALL PRIVILEGES ON oktest.* TO 'okdev'@'localhost';
