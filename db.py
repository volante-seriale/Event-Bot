import json
import sqlite3

from config import DB_PATH


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            message_id TEXT PRIMARY KEY,
            data TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def load_all_events():
    conn = _get_conn()
    rows = conn.execute("SELECT message_id, data FROM events").fetchall()
    conn.close()
    return {row["message_id"]: json.loads(row["data"]) for row in rows}


def save_event(message_id, data):
    conn = _get_conn()
    conn.execute(
        "INSERT INTO events (message_id, data) VALUES (?, ?) "
        "ON CONFLICT(message_id) DO UPDATE SET data = excluded.data",
        (str(message_id), json.dumps(data)),
    )
    conn.commit()
    conn.close()


def delete_event(message_id):
    conn = _get_conn()
    conn.execute("DELETE FROM events WHERE message_id = ?", (str(message_id),))
    conn.commit()
    conn.close()
