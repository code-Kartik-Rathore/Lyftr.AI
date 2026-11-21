"""SQLite database setup using aiosqlite."""

import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Tuple

import aiosqlite

from app.config import settings

_DB_PATH: Optional[str] = None


def _resolve_db_path() -> str:
    """Extract the file path from the DATABASE_URL."""
    url = settings.database_url
    # sqlite:////data/app.db -> /data/app.db
    path = url[len("sqlite:///"):] if url.startswith("sqlite:///") else url
    if path.startswith("/data"):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except (PermissionError, OSError):
            rel_dir = os.path.join(os.getcwd(), "data")
            os.makedirs(rel_dir, exist_ok=True)
            path = os.path.join(rel_dir, os.path.basename(path))
    return path


def get_db_path() -> str:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = _resolve_db_path()
    return _DB_PATH


async def init_db() -> None:
    """Create the database schema if it doesn't exist."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)"
        )
        await db.commit()


async def save_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[dict] = None,
) -> None:
    """Persist a single message to the database."""
    db_path = get_db_path()
    meta_json = json.dumps(metadata) if metadata else None
    now = datetime.now(timezone.utc).isoformat()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, meta_json, now),
        )
        await db.commit()


async def get_session_messages(session_id: str) -> List[dict]:
    """Return all messages for a session, ordered oldest first."""
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT role, content, metadata FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        results = []
        for row in rows:
            entry: dict = {"role": row["role"], "content": row["content"]}
            if row["metadata"]:
                entry["metadata"] = json.loads(row["metadata"])
            results.append(entry)
        return results


async def session_exists(session_id: str) -> bool:
    """Check whether any messages exist for the given session."""
    db_path = get_db_path()
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT 1 FROM messages WHERE session_id = ? LIMIT 1",
            (session_id,),
        )
        row = await cursor.fetchone()
        return row is not None
