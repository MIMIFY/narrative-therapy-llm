import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiosqlite

from .config import settings


async def init_db() -> None:
    """Create tables if they do not exist."""
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                participant_id TEXT DEFAULT '',
                stage TEXT DEFAULT 'trust building',
                stage_count INTEGER DEFAULT 0,
                accomplish_goal INTEGER DEFAULT 0,
                turns TEXT DEFAULT '[]'
            )
            """
        )
        await db.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_session(session_id: str, participant_id: str = "") -> None:
    """Insert a new session row."""
    now = _now_iso()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO sessions
                (id, created_at, updated_at, participant_id, stage, stage_count, accomplish_goal, turns)
            VALUES (?, ?, ?, ?, 'trust building', 0, 0, '[]')
            """,
            (session_id, now, now, participant_id),
        )
        await db.commit()


async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Return a session as a dict, or None if not found."""
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)


async def update_session(
    session_id: str,
    stage: str,
    stage_count: int,
    accomplish_goal: int,
    turns_json: str,
) -> None:
    """Update mutable fields of a session."""
    now = _now_iso()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            UPDATE sessions
            SET updated_at = ?,
                stage = ?,
                stage_count = ?,
                accomplish_goal = ?,
                turns = ?
            WHERE id = ?
            """,
            (now, stage, stage_count, accomplish_goal, turns_json, session_id),
        )
        await db.commit()


async def list_sessions() -> List[Dict[str, Any]]:
    """Return a summary list of all sessions with turn count and last message preview."""
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, created_at, updated_at, participant_id, stage, stage_count, turns
               FROM sessions ORDER BY updated_at DESC"""
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                turns = json.loads(d.pop("turns", "[]"))
                d["turn_count"] = len(turns)
                last_client = turns[-1].get("client", "") if turns else ""
                d["preview"] = (last_client[:60] + "…") if len(last_client) > 60 else last_client
                result.append(d)
            return result
