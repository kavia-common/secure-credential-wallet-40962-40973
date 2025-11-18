# Migrations

This folder contains SQL migrations for PostgreSQL environments. The development environment uses SQLite but maintains schema parity with production Postgres via these files.

Files:
- 001_init.sql: Initial schema for users, credentials, shares, ekyc_sessions, and audit_logs.

Usage (Postgres):
1. Ensure you have a Postgres connection (DB_URL).
2. Apply migrations in order, e.g.:
   psql "$DB_URL" -f migrations/001_init.sql

Dev (SQLite):
- The dev database is created by init_db.py and mirrors this schema.
- Foreign keys, indexes, and basic defaults are set to match the Postgres behavior where feasible.
