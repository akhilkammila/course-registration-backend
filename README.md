# course-registration-backend

Steps to create the SQL Database:

CREATE DATABASE course_registration;

\c course_registration;

CREATE TABLE users (
  email VARCHAR(255) PRIMARY KEY,
  password VARCHAR(255) NOT NULL
);

Using sql:
psql -d postgres
\c course_registration;
SELECT * FROM users;

Running server:
Run and use postmal for post requests
Get request in browser for testing

Testing endpoints:
