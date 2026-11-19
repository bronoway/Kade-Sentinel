import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).with_name("trays.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS trays (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    location TEXT
);
CREATE TABLE IF NOT EXISTS permissions (
    id         INTEGER PRIMARY KEY,
    tray_id    INTEGER NOT NULL REFERENCES trays(id),
    granted_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    active     INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS alerts (
    id           INTEGER PRIMARY KEY,
    tray_id      INTEGER NOT NULL REFERENCES trays(id),
    message      TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    acknowledged INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_perm_tray  ON permissions(tray_id, active, expires_at);
CREATE INDEX IF NOT EXISTS idx_alert_tray ON alerts(tray_id, acknowledged);
"""


def utc_iso(offset_minutes: int = 0) -> str:
    t = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db():
    con = sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
    finally:
        con.close()


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode = WAL")
    with con:
        con.executescript(SCHEMA)
        if con.execute("SELECT COUNT(*) FROM trays").fetchone()[0] == 0:
            con.execute("INSERT INTO trays (name, location) VALUES ('Tray 1 - Biscuits', 'Front counter')")
    con.close()
