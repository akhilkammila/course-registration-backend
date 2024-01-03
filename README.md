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


Dockerfile backend:
docker build -f Dockerfile.backend -t course-registration-backend:1 .
docker run \
  -e WEBPAGE_BASE_URL='http://127.0.0.1:3000' \
  -e SQLALCHEMY_DATABASE_URI='postgresql://user:password@database-container:5432/course_registration' \
  -p 5000:5000 \
  -d course-registration-backend:1

Dockerfile database:
docker build -f Dockerfile.database -t course-registration-database:1 .
docker run --name database-container \
  -e POSTGRES_DB=course_registration \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -d course-registration-database:1