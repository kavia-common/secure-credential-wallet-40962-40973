#!/usr/bin/env python3
"""
Validate SQLite database schema presence.

Checks existence of tables:
- users
- credentials
- shares
- ekyc_sessions
- audit_logs
"""

import sqlite3
import sys
import os
from typing import Set

DB_NAME = "myapp.db"
REQUIRED_TABLES: Set[str] = {
    "users",
    "credentials",
    "shares",
    "ekyc_sessions",
    "audit_logs",
}

def main() -> int:
    if not os.path.exists(DB_NAME):
        print(f"Database file '{DB_NAME}' not found")
        return 1

    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys = ON;")
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            existing = {row[0] for row in cur.fetchall()}
            missing = REQUIRED_TABLES - existing

            if missing:
                print("Missing tables:", ", ".join(sorted(missing)))
                print("Existing tables:", ", ".join(sorted(existing)))
                return 1

            print("All required tables are present.")
            return 0
    except sqlite3.Error as e:
        print(f"Schema validation failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
