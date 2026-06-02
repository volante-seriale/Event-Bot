import json

from psycopg2.extras import Json
from psycopg2.pool import ThreadedConnectionPool

from config import DATABASE_URL

_pool: ThreadedConnectionPool | None = None


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = ThreadedConnectionPool(minconn=1, maxconn=5, dsn=DATABASE_URL)
    return _pool


def init_db():
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    message_id TEXT PRIMARY KEY,
                    data JSONB NOT NULL
                )
            """)
        conn.commit()
    finally:
        pool.putconn(conn)


def load_all_events():
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT message_id, data FROM events")
            rows = cur.fetchall()
    finally:
        pool.putconn(conn)
    return {
        row[0]: row[1] if isinstance(row[1], dict) else json.loads(row[1])
        for row in rows
    }


def save_event(message_id, data):
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (message_id, data) VALUES (%s, %s)
                ON CONFLICT (message_id) DO UPDATE SET data = excluded.data
                """,
                (str(message_id), Json(data)),
            )
        conn.commit()
    finally:
        pool.putconn(conn)


def delete_event(message_id):
    pool = _get_pool()
    conn = pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM events WHERE message_id = %s", (str(message_id),))
        conn.commit()
    finally:
        pool.putconn(conn)
