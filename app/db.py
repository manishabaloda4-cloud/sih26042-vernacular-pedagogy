"""SQLite helpers. The phrase bank = verified Hindi -> target-language sentences + a cache
of machine translations, so repeated classroom sentences are instant."""
import os
import sqlite3
from datetime import datetime, timezone

DATA_DIR = os.environ.get("DATA_DIR", "data")
DB_PATH = os.path.join(DATA_DIR, "pedagogy.db")
TTS_DIR = os.path.join(DATA_DIR, "tts")

SCHEMA = """
CREATE TABLE IF NOT EXISTS phrases (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    hindi        TEXT NOT NULL,
    hindi_norm   TEXT NOT NULL,
    lang         TEXT NOT NULL DEFAULT 'pa',   -- target language code (pa = Punjabi)
    target_text  TEXT NOT NULL DEFAULT '',     -- e.g. Gurmukhi text
    category     TEXT NOT NULL DEFAULT 'general',
    grade        INTEGER,
    outcome_code TEXT NOT NULL DEFAULT '',     -- NIPUN Bharat learning outcome
    verified     INTEGER NOT NULL DEFAULT 0,   -- 1 = checked by a native speaker
    source       TEXT NOT NULL DEFAULT 'human',-- 'human' or 'machine'
    updated_at   TEXT NOT NULL,
    UNIQUE (hindi_norm, lang)
);
CREATE INDEX IF NOT EXISTS idx_phrases_filter ON phrases(lang, category, grade);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TTS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def get_conn():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
