"""
Safe SQLite helper — prevents SQL injection by enforcing parameterized queries.
Import and use `safe_execute(conn, sql, params)` for every write/read.
"""
import re
import sqlite3
from typing import Iterable, Any

_FORBIDDEN = re.compile(
    r"\b(DROP|ALTER|TRUNCATE|EXEC(UTE)?|xp_|UNION\s+SELECT)\b",
    re.IGNORECASE,
)

def safe_execute(conn: sqlite3.Connection, sql: str,
                 params: Iterable[Any] = ()) -> sqlite3.Cursor:
    if _FORBIDDEN.search(sql):
        raise ValueError("Forbidden SQL pattern detected.")
    if "%" in sql and not params:
        # String formatting with no params is a red flag.
        raise ValueError("Use ? placeholders with params tuple; never f-strings.")
    return conn.execute(sql, tuple(params))

def safe_executemany(conn, sql, seq):
    if _FORBIDDEN.search(sql):
        raise ValueError("Forbidden SQL pattern detected.")
    return conn.executemany(sql, seq)
