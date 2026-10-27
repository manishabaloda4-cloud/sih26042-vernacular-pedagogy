"""SQLite helpers. Content is versioned so tablets can sync only what changed."""
import os
import sqlite3
from datetime import datetime, timezone

DATA_DIR = os.environ.get("DATA_DIR", "data")
DB_PATH = os.path.join(DATA_DIR, "content.db")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS phrases (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    hindi         TEXT NOT NULL,
    hindi_norm    TEXT NOT NULL UNIQUE,
    santali       TEXT NOT NULL DEFAULT '',   -- Ol Chiki script
    santali_latin TEXT NOT NULL DEFAULT '',   -- romanised / Devanagari fallback
    category      TEXT NOT NULL DEFAULT 'general',
    grade         INTEGER,
    outcome_code  TEXT NOT NULL DEFAULT '',   -- NIPUN Bharat learning outcome
    audio_file    TEXT NOT NULL DEFAULT '',
    verified      INTEGER NOT NULL DEFAULT 0, -- 1 = checked by a native speaker
    deleted       INTEGER NOT NULL DEFAULT 0, -- tombstone so tablets can remove it
    version       INTEGER NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_phrases_version ON phrases(version);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    os.makedirs(AUDIO_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect()
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR IGNORE INTO meta(key, value) VALUES ('version', '0')")
    conn.commit()
    conn.close()


def get_conn():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT value FROM meta WHERE key='version'").fetchone()[0])


def bump_version(conn: sqlite3.Connection) -> int:
    v = current_version(conn) + 1
    conn.execute("UPDATE meta SET value=? WHERE key='version'", (str(v),))
    return v
