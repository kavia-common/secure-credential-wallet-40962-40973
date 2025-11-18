#!/usr/bin/env python3
"""
Initialize development database for database_postgres.

This script sets up a SQLite database (dev) with schema parity to Postgres,
including tables:
- users
- credentials
- shares
- ekyc_sessions
- audit_logs

It also:
- Enables foreign keys and WAL mode for SQLite
- Creates useful indexes
- Seeds minimal app_info
- Writes db_connection.txt
- Writes .env with DB_URL and SQLITE_DB
- Writes db_visualizer/sqlite.env for the local visualizer

Security notes:
- No sensitive secrets are logged.
- Only local file paths are written.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Iterable


DB_NAME = "myapp.db"


def _execute_many(cursor: sqlite3.Cursor, statements: Iterable[str]) -> None:
    """Execute multiple SQL statements safely, skipping empties."""
    for stmt in statements:
        s = (stmt or "").strip()
        if not s:
            continue
        cursor.execute(s)


# PUBLIC_INTERFACE
def init_sqlite_db(db_path: str = DB_NAME) -> None:
    """Initialize the SQLite database with the full schema and indexes."""
    first_time = not os.path.exists(db_path)

    # Ensure directory exists
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")

        cur = conn.cursor()

        # Schema to mimic Postgres (types chosen for compatibility)
        schema_statements = [
            # Minimal app info
            """
            CREATE TABLE IF NOT EXISTS app_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            # Users table
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                username TEXT UNIQUE,
                password_hash TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """,
            # Credentials owned by users
            """
            CREATE TABLE IF NOT EXISTS credentials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                data_encrypted BLOB NOT NULL,
                iv BLOB, -- initialization vector (optional if embedded)
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            # Sharing records: who can access which credential
            """
            CREATE TABLE IF NOT EXISTS shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                credential_id INTEGER NOT NULL,
                shared_with_user_id INTEGER NOT NULL,
                permission TEXT NOT NULL DEFAULT 'read', -- read|write
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (credential_id) REFERENCES credentials(id) ON DELETE CASCADE,
                FOREIGN KEY (shared_with_user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE (credential_id, shared_with_user_id)
            );
            """,
            # eKYC sessions
            """
            CREATE TABLE IF NOT EXISTS ekyc_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending', -- pending|verified|failed
                provider TEXT,
                reference_id TEXT,
                result_json TEXT, -- store normalized result snapshot
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """,
            # Audit logs
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            """,
            # Indexes
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
            "CREATE INDEX IF NOT EXISTS idx_credentials_user_id ON credentials(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_shares_credential_id ON shares(credential_id);",
            "CREATE INDEX IF NOT EXISTS idx_shares_shared_with_user_id ON shares(shared_with_user_id);",
            "CREATE INDEX IF NOT EXISTS idx_ekyc_user_id ON ekyc_sessions(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_logs(created_at);",
        ]

        _execute_many(cur, schema_statements)

        # Seed minimal app_info
        cur.execute(
            "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
            ("project_name", "database_postgres"),
        )
        cur.execute(
            "INSERT OR REPLACE INTO app_info (key, value) VALUES (?, ?)",
            ("version", "0.2.0"),
        )

        conn.commit()

    # Write connection info and env after successful schema creation
    write_connection_files(db_path, first_time=first_time)


def write_connection_files(db_path: str, first_time: bool) -> None:
    """Write db_connection.txt, .env, and db_visualizer/sqlite.env files."""
    current_dir = os.getcwd()
    absolute_path = os.path.abspath(db_path)
    connection_string = f"sqlite:///{absolute_path}"

    # db_connection.txt
    try:
        with open("db_connection.txt", "w") as f:
            f.write("# SQLite connection methods:\n")
            f.write(f"# Python: sqlite3.connect('{db_path}')\n")
            f.write(f"# Connection string: {connection_string}\n")
            f.write(f"# File path: {absolute_path}\n")
        print("Connection information saved to db_connection.txt")
    except Exception as e:
        print(f"Warning: Could not save connection info: {e}")

    # .env with DB_URL and SQLITE_DB
    try:
        with open(".env", "w") as f:
            f.write("# Auto-generated by init_db.py\n")
            f.write(f"DB_URL={connection_string}\n")
            f.write(f"SQLITE_DB={absolute_path}\n")
        print("Environment variables saved to .env")
    except Exception as e:
        print(f"Warning: Could not write .env: {e}")

    # Visualizer env
    try:
        os.makedirs("db_visualizer", exist_ok=True)
        with open("db_visualizer/sqlite.env", "w") as f:
            f.write(f'export SQLITE_DB="{absolute_path}"\n')
        print("Visualizer environment saved to db_visualizer/sqlite.env")
    except Exception as e:
        print(f"Warning: Could not write db_visualizer/sqlite.env: {e}")

    print("")
    print("SQLite setup complete!")
    print(f"Database: {os.path.basename(db_path)}")
    print(f"Location: {absolute_path}")
    if first_time:
        print("Initialized a new database file.")
    else:
        print("Verified existing database and ensured schema is present.")
    print("")


def main() -> None:
    """Entrypoint for CLI usage."""
    init_sqlite_db(DB_NAME)


if __name__ == "__main__":
    main()
