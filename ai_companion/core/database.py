import sqlite3
import hashlib
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from ai_companion.core.paths import data_path

_DB_PATH = data_path("companion.db")
_local = threading.local()


def _connect() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return _local.conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS Conversations (
            conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL REFERENCES Users(user_id),
            title           TEXT NOT NULL DEFAULT 'New Chat',
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS Messages (
            message_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL REFERENCES Conversations(conversation_id),
            role            TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
            content         TEXT NOT NULL,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS Detected_Errors (
            error_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES Users(user_id),
            language    TEXT NOT NULL DEFAULT 'unknown',
            error_type  TEXT NOT NULL DEFAULT '',
            error_message TEXT NOT NULL DEFAULT '',
            solution    TEXT NOT NULL DEFAULT '',
            severity    TEXT NOT NULL DEFAULT 'info',
            file_name   TEXT NOT NULL DEFAULT '',
            line_number INTEGER NOT NULL DEFAULT 0,
            fingerprint TEXT NOT NULL DEFAULT '',
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS Memory (
            memory_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES Users(user_id),
            memory_key   TEXT NOT NULL,
            memory_value TEXT NOT NULL DEFAULT '',
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS Settings (
            setting_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES Users(user_id),
            setting_name TEXT NOT NULL,
            setting_value TEXT NOT NULL DEFAULT '',
            UNIQUE(user_id, setting_name)
        );

        CREATE INDEX IF NOT EXISTS idx_messages_conv ON Messages(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_messages_role ON Messages(role);
        CREATE INDEX IF NOT EXISTS idx_errors_user ON Detected_Errors(user_id);
        CREATE INDEX IF NOT EXISTS idx_errors_fingerprint ON Detected_Errors(fingerprint);
        CREATE INDEX IF NOT EXISTS idx_memory_user ON Memory(user_id);
        CREATE INDEX IF NOT EXISTS idx_settings_user ON Settings(user_id);
    """)
    conn.commit()
    _ensure_default_user(conn)


def _ensure_default_user(conn: sqlite3.Connection):
    row = conn.execute("SELECT user_id FROM Users LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO Users (username) VALUES (?)", ("default",))
        conn.commit()


def _get_user_id(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT user_id FROM Users LIMIT 1").fetchone()
    if row is None:
        conn.execute("INSERT INTO Users (username) VALUES (?)", ("default",))
        conn.commit()
        row = conn.execute("SELECT user_id FROM Users LIMIT 1").fetchone()
    return row["user_id"]


def _fingerprint(error_type: str, message: str, file_name: str, line_number: int) -> str:
    raw = f"{error_type}|{message}|{file_name}|{line_number}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# ── Conversations ──────────────────────────────────────────

def save_message(conversation_id: int, role: str, content: str) -> int:
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO Messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content),
    )
    conn.commit()
    return cur.lastrowid


def get_conversations(user_id: Optional[int] = None) -> list[dict]:
    conn = _connect()
    if user_id is None:
        user_id = _get_user_id(conn)
    rows = conn.execute(
        "SELECT * FROM Conversations WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def create_conversation(title: str = "New Chat", user_id: Optional[int] = None) -> int:
    conn = _connect()
    if user_id is None:
        user_id = _get_user_id(conn)
    cur = conn.execute(
        "INSERT INTO Conversations (user_id, title) VALUES (?, ?)",
        (user_id, title),
    )
    conn.commit()
    return cur.lastrowid


def get_messages_for_conversation(conversation_id: int) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM Messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Errors ─────────────────────────────────────────────────

def save_error(language: str, error_type: str, error_message: str,
               solution: str = "", severity: str = "info",
               file_name: str = "", line_number: int = 0) -> int:
    conn = _connect()
    user_id = _get_user_id(conn)
    fp = _fingerprint(error_type, error_message, file_name, line_number)
    existing = conn.execute(
        "SELECT error_id FROM Detected_Errors WHERE fingerprint = ?", (fp,)
    ).fetchone()
    if existing:
        return existing["error_id"]
    cur = conn.execute(
        """INSERT INTO Detected_Errors
           (user_id, language, error_type, error_message, solution, severity, file_name, line_number, fingerprint)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, language, error_type, error_message, solution, severity, file_name, line_number, fp),
    )
    conn.commit()
    return cur.lastrowid


def load_history(user_id: Optional[int] = None) -> list[dict]:
    conn = _connect()
    if user_id is None:
        user_id = _get_user_id(conn)
    rows = conn.execute(
        "SELECT * FROM Detected_Errors WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def clear_history(user_id: Optional[int] = None):
    conn = _connect()
    if user_id is None:
        user_id = _get_user_id(conn)
    conn.execute("DELETE FROM Detected_Errors WHERE user_id = ?", (user_id,))
    conn.commit()


def purge_generic_history(user_id: Optional[int] = None):
    conn = _connect()
    if user_id is None:
        user_id = _get_user_id(conn)
    conn.execute(
        "DELETE FROM Detected_Errors WHERE user_id = ? AND error_type = ?",
        (user_id, "GenericError"),
    )
    conn.commit()


# ── Memory ─────────────────────────────────────────────────

def save_memory(key: str, value: str) -> int:
    conn = _connect()
    user_id = _get_user_id(conn)
    existing = conn.execute(
        "SELECT memory_id FROM Memory WHERE user_id = ? AND memory_key = ?",
        (user_id, key),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE Memory SET memory_value = ? WHERE memory_id = ?",
            (value, existing["memory_id"]),
        )
        conn.commit()
        return existing["memory_id"]
    cur = conn.execute(
        "INSERT INTO Memory (user_id, memory_key, memory_value) VALUES (?, ?, ?)",
        (user_id, key, value),
    )
    conn.commit()
    return cur.lastrowid


def get_all_memory(user_id: Optional[int] = None) -> list[dict]:
    conn = _connect()
    if user_id is None:
        user_id = _get_user_id(conn)
    rows = conn.execute(
        "SELECT * FROM Memory WHERE user_id = ? ORDER BY memory_key ASC",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def delete_memory(memory_id: int):
    conn = _connect()
    conn.execute("DELETE FROM Memory WHERE memory_id = ?", (memory_id,))
    conn.commit()


# ── Settings ───────────────────────────────────────────────

def save_settings(name: str, value: str):
    conn = _connect()
    user_id = _get_user_id(conn)
    conn.execute(
        """INSERT INTO Settings (user_id, setting_name, setting_value)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id, setting_name) DO UPDATE SET setting_value = excluded.setting_value""",
        (user_id, name, value),
    )
    conn.commit()


def get_setting(name: str, default: str = "") -> str:
    conn = _connect()
    user_id = _get_user_id(conn)
    row = conn.execute(
        "SELECT setting_value FROM Settings WHERE user_id = ? AND setting_name = ?",
        (user_id, name),
    ).fetchone()
    return row["setting_value"] if row else default


def get_all_settings(user_id: Optional[int] = None) -> dict[str, str]:
    conn = _connect()
    if user_id is None:
        user_id = _get_user_id(conn)
    rows = conn.execute(
        "SELECT setting_name, setting_value FROM Settings WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return {r["setting_name"]: r["setting_value"] for r in rows}
