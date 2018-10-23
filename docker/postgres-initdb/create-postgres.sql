DO $do$
BEGIN
  CREATE EXTENSION IF NOT EXISTS dblink;
  IF EXISTS (
      SELECT
        1
      FROM
        pg_database
      WHERE
        datname = 'scry') THEN
      RAISE NOTICE 'Database already exists';
  ELSE
    PERFORM
      dblink_exec('dbname=' || current_database(), 'CREATE DATABASE scry');
  END IF;
  PERFORM
    dblink_exec('dbname=scry', 'CREATE SCHEMA IF NOT EXISTS scry2;');
END $do$;

