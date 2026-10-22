"""SQLite for local use; PostgreSQL via DATABASE_URL for persistent hosted deployments."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime, timezone

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
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError("DATABASE_URL menggunakan PostgreSQL tetapi psycopg belum terpasang.") from exc
        conn = psycopg.connect(DATABASE_URL, connect_timeout=10, row_factory=dict_row)
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitored_targets (
                    id BIGSERIAL PRIMARY KEY,
                    target TEXT NOT NULL UNIQUE,
                    enabled BOOLEAN NOT NULL DEFAULT FALSE,
                    interval_hours INTEGER NOT NULL DEFAULT 24,
                    created_at TEXT NOT NULL
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS monitored_targets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target TEXT NOT NULL UNIQUE,
                    enabled INTEGER NOT NULL DEFAULT 0,
                    interval_hours INTEGER NOT NULL DEFAULT 24,
                    created_at TEXT NOT NULL
                )
            """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_target_time ON snapshots(target, collected_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_monitored_targets_enabled ON monitored_targets(enabled)")


def add_target(target: str, interval_hours: int = 24):
    interval_hours = int(interval_hours)
    if interval_hours not in (1, 6, 12, 24, 168):
        raise ValueError("Interval harus 1, 6, 12, 24, atau 168 jam.")
    with get_connection() as conn:
        # New targets are intentionally disabled until an operator confirms authorization.
        if IS_POSTGRES:
            conn.execute(
                "INSERT INTO monitored_targets(target, enabled, interval_hours, created_at) VALUES (?, FALSE, ?, ?) ON CONFLICT(target) DO NOTHING",
                (target, interval_hours, datetime.now(timezone.utc).isoformat()),
            )
        else:
            conn.execute(
                "INSERT OR IGNORE INTO monitored_targets(target, enabled, interval_hours, created_at) VALUES (?, 0, ?, ?)",
                (target, interval_hours, datetime.now(timezone.utc).isoformat()),
            )


def get_targets(enabled_only: bool = False) -> list[dict]:
    query = "SELECT id, target, enabled, interval_hours, created_at FROM monitored_targets"
    if enabled_only:
        query += " WHERE enabled = " + ("TRUE" if IS_POSTGRES else "1")
    query += " ORDER BY id"
    with get_connection() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


def set_target_enabled(target_id: int, enabled: bool):
    with get_connection() as conn:
        conn.execute(
            _sql("UPDATE monitored_targets SET enabled = ? WHERE id = ?"),
            (bool(enabled) if IS_POSTGRES else int(bool(enabled)), int(target_id)),
        )


def remove_target(target_id: int):
    with get_connection() as conn:
        conn.execute(_sql("DELETE FROM monitored_targets WHERE id = ?"), (int(target_id),))


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
