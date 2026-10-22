"""SQLite for local use; PostgreSQL via DATABASE_URL for persistent hosted deployments."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
IS_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))
DB_PATH = Path(os.environ.get("OSINT_DB_PATH", "data/osint.db"))
if not IS_POSTGRES:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_connection():
    if IS_POSTGRES:
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("DATABASE_URL menggunakan PostgreSQL tetapi psycopg belum terpasang.") from exc
        conn = psycopg.connect(DATABASE_URL, connect_timeout=10)
        try:
            with conn:
                yield conn
        finally:
            conn.close()
    else:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()


def _sql(statement: str) -> str:
    return statement.replace("?", "%s") if IS_POSTGRES else statement


def initialize_database():
    with get_connection() as conn:
        if IS_POSTGRES:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id BIGSERIAL PRIMARY KEY,
                    target TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    content_json TEXT NOT NULL
                )
            """)
        else:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT NOT NULL,
                    collected_at TEXT NOT NULL,
                    content_json TEXT NOT NULL
                )
            """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_target_time ON snapshots(target, collected_at DESC)")


def save_snapshot(target: str, content: dict):
    with get_connection() as conn:
        conn.execute(
            _sql("INSERT INTO snapshots (target, collected_at, content_json) VALUES (?, ?, ?)"),
            (target, content["collected_at"], json.dumps(content, ensure_ascii=False)),
        )


def get_snapshots(target: str, limit: int = 50) -> list[dict]:
    limit = max(1, min(int(limit), 500))
    with get_connection() as conn:
        rows = conn.execute(
            _sql("SELECT id, target, collected_at, content_json FROM snapshots WHERE target = ? ORDER BY id DESC LIMIT ?"),
            (target, limit),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "target": row["target"],
            "collected_at": row["collected_at"],
            "content": json.loads(row["content_json"]),
        }
        for row in rows
    ]
