-- Note: need to create database vipar 
-- CREATE DATABASE `vipar`


-- Additional statements
INSERT into variables_type (type) VALUES ('Categorical');
INSERT into variables_type (type) VALUES ('Continuous');
INSERT into variables_type (type) VALUES ('Date');

INSERT into studyprivs (description) VALUES ('standard user');
INSERT into studyprivs (description) VALUES ('study lead');
INSERT into studyprivs (description) VALUES ('data certification coordinator');

INSERT into users (username,password,time_zone,email,it) VALUES ('viparadmin','geatNinuaR','Australia/Perth','bioinformatics@ichr.uwa.edu.au',1);

-- Set User priviliges
GRANT SELECT ON `vipar`.* TO 'viparselect'@'localhost' identified by 'geatNinuaR';
GRANT SELECT, INSERT, UPDATE, DELETE, LOCK TABLES ON `vipar`.* TO 'viparinsup'@'localhost' identified by 'geatNinuaR';

-- Flush Privs
FLUSH PRIVILEGES;

