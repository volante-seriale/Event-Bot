import json

import psycopg2
from psycopg2.extras import Json

from config import DATABASE_URL


def _get_conn():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            message_id TEXT PRIMARY KEY,
            data JSONB NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def load_all_events():
    conn = _get_conn()
    rows = conn.execute("SELECT message_id, data FROM events").fetchall()
    conn.close()
    return {
        row[0]: row[1] if isinstance(row[1], dict) else json.loads(row[1])
        for row in rows
    }


def save_event(message_id, data):
    conn = _get_conn()
    conn.execute(
        """
        INSERT INTO events (message_id, data) VALUES (%s, %s)
        ON CONFLICT (message_id) DO UPDATE SET data = excluded.data
        """,
        (str(message_id), Json(data)),
    )
    conn.commit()
    conn.close()


def delete_event(message_id):
    conn = _get_conn()
    conn.execute("DELETE FROM events WHERE message_id = %s", (str(message_id),))
    conn.commit()
    conn.close()
