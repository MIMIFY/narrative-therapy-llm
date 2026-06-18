import asyncio
import json
from datetime import datetime, timezone
import uuid
from typing import Any, Dict, List, Optional

import aiosqlite

from .config import settings

_session_write_lock = asyncio.Lock()


def normalize_participant_id(participant_id: str = "") -> str:
    """Normalize only accidental leading/trailing spaces; internal spaces are meaningful."""
    return str(participant_id or "").strip()


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
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS participant_memories (
                id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                stage TEXT DEFAULT '',
                confidence REAL DEFAULT 0.7,
                source_session_id TEXT DEFAULT '',
                source_turn INTEGER DEFAULT 0,
                valid_from TEXT NOT NULL,
                valid_to TEXT DEFAULT NULL,
                superseded_by TEXT DEFAULT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS narrative_trajectories (
                id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL,
                title TEXT NOT NULL,
                before_text TEXT DEFAULT '',
                turning_points TEXT DEFAULT '[]',
                now_text TEXT DEFAULT '',
                preferred_story TEXT DEFAULT '',
                evidence TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS session_summaries (
                session_id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL,
                summary TEXT DEFAULT '',
                open_threads TEXT DEFAULT '[]',
                current_stage TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS participant_story_cards (
                participant_id TEXT PRIMARY KEY,
                story_markdown TEXT NOT NULL,
                source_turn_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS participant_story_card_history (
                id TEXT PRIMARY KEY,
                participant_id TEXT NOT NULL,
                story_markdown TEXT NOT NULL,
                source_turn_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.execute(
            """
            INSERT OR IGNORE INTO participant_story_card_history
                (id, participant_id, story_markdown, source_turn_count, created_at)
            SELECT
                participant_id || ':' || source_turn_count,
                participant_id,
                story_markdown,
                source_turn_count,
                created_at
            FROM participant_story_cards
            """
        )
        await db.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_session(session_id: str, participant_id: str = "") -> None:
    """Insert a new session row."""
    now = _now_iso()
    participant_id = normalize_participant_id(participant_id)
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
    async with _session_write_lock:
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


async def append_session_turn(
    session_id: str,
    stage: str,
    stage_count: int,
    accomplish_goal: int,
    turn: Dict[str, Any],
) -> None:
    """Append or replace one turn while preserving traces already written to older turns."""
    now = _now_iso()
    async with _session_write_lock:
        async with aiosqlite.connect(settings.database_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT turns FROM sessions WHERE id = ?", (session_id,)) as cursor:
                row = await cursor.fetchone()
            if row is None:
                return

            turns = json.loads(row["turns"] or "[]")
            turn_round = int(turn.get("round", len(turns) + 1))
            if len(turns) >= turn_round:
                existing = turns[turn_round - 1]
                merged = dict(turn)
                existing_trace = existing.get("trace") or {}
                new_trace = merged.get("trace") or {}
                if existing_trace and not new_trace.get("goal_check"):
                    merged["trace"] = {**new_trace, **existing_trace}
                turns[turn_round - 1] = merged
            else:
                turns.append(turn)

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
                (
                    now,
                    stage,
                    stage_count,
                    accomplish_goal,
                    json.dumps(turns, ensure_ascii=False),
                    session_id,
                ),
            )
            await db.commit()


async def update_accomplish_goal(session_id: str, achieved: bool) -> None:
    """Atomically flip only the accomplish_goal flag — never touches turns or stage."""
    now = _now_iso()
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            "UPDATE sessions SET accomplish_goal = ?, updated_at = ? WHERE id = ?",
            (1 if achieved else 0, now, session_id),
        )
        await db.commit()


async def update_turn_trace(
    session_id: str,
    turn_round: int,
    trace: Dict[str, Any],
    accomplish_goal: Optional[bool] = None,
) -> None:
    """Patch one turn's trace without overwriting newer turns."""
    now = _now_iso()
    async with _session_write_lock:
        async with aiosqlite.connect(settings.database_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT turns, accomplish_goal FROM sessions WHERE id = ?", (session_id,)) as cursor:
                row = await cursor.fetchone()
            if row is None:
                return

            turns = json.loads(row["turns"] or "[]")
            patched = False
            for turn in turns:
                if int(turn.get("round", 0)) == int(turn_round):
                    turn["trace"] = trace
                    patched = True
                    break
            if not patched:
                return

            if accomplish_goal is None:
                goal_value = int(row["accomplish_goal"] or 0)
            else:
                goal_value = 1 if accomplish_goal else 0

            await db.execute(
                """
                UPDATE sessions
                SET updated_at = ?,
                    accomplish_goal = ?,
                    turns = ?
                WHERE id = ?
                """,
                (now, goal_value, json.dumps(turns, ensure_ascii=False), session_id),
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


async def list_sessions_by_participant(participant_id: str) -> List[Dict[str, Any]]:
    """Return session summaries for one participant ID."""
    participant_id = normalize_participant_id(participant_id)
    if not participant_id:
        return []

    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, created_at, updated_at, participant_id, stage, stage_count, turns
               FROM sessions
               WHERE participant_id = ?
               ORDER BY updated_at DESC""",
            (participant_id,),
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


async def get_participant_sessions_full(participant_id: str) -> List[Dict[str, Any]]:
    """Return full sessions for one participant, including parsed turns."""
    participant_id = normalize_participant_id(participant_id)
    if not participant_id:
        return []

    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM sessions
               WHERE participant_id = ?
               ORDER BY created_at ASC""",
            (participant_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["turns"] = json.loads(d.get("turns") or "[]")
                result.append(d)
            return result


async def count_participant_turns(participant_id: str) -> int:
    """Count all stored turns for one participant."""
    sessions = await get_participant_sessions_full(participant_id)
    return sum(len(s.get("turns", [])) for s in sessions)


async def upsert_session_summary(
    session_id: str,
    participant_id: str,
    summary: str,
    open_threads: List[str],
    current_stage: str,
) -> None:
    now = _now_iso()
    participant_id = normalize_participant_id(participant_id)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            INSERT INTO session_summaries
                (session_id, participant_id, summary, open_threads, current_stage, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                participant_id = excluded.participant_id,
                summary = excluded.summary,
                open_threads = excluded.open_threads,
                current_stage = excluded.current_stage,
                updated_at = excluded.updated_at
            """,
            (
                session_id,
                participant_id,
                summary,
                json.dumps(open_threads, ensure_ascii=False),
                current_stage,
                now,
            ),
        )
        await db.commit()


async def get_session_summary(session_id: str) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM session_summaries WHERE session_id = ?",
            (session_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            d = dict(row)
            d["open_threads"] = json.loads(d.get("open_threads") or "[]")
            return d


async def insert_participant_memory(memory: Dict[str, Any]) -> None:
    now = _now_iso()
    memory = dict(memory)
    memory["participant_id"] = normalize_participant_id(memory.get("participant_id", ""))
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO participant_memories
                (id, participant_id, memory_type, content, stage, confidence,
                 source_session_id, source_turn, valid_from, valid_to, superseded_by,
                 metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory["id"],
                memory["participant_id"],
                memory.get("memory_type", "observation"),
                memory["content"],
                memory.get("stage", ""),
                float(memory.get("confidence", 0.7)),
                memory.get("source_session_id", ""),
                int(memory.get("source_turn", 0)),
                memory.get("valid_from") or now,
                memory.get("valid_to"),
                memory.get("superseded_by"),
                json.dumps(memory.get("metadata", {}), ensure_ascii=False),
                memory.get("created_at") or now,
                now,
            ),
        )
        await db.commit()


async def list_participant_memories(participant_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    participant_id = normalize_participant_id(participant_id)
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM participant_memories
               WHERE participant_id = ? AND valid_to IS NULL
               ORDER BY updated_at DESC
               LIMIT ?""",
            (participant_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["metadata"] = json.loads(d.get("metadata") or "{}")
                result.append(d)
            return result


async def upsert_narrative_trajectory(trajectory: Dict[str, Any]) -> None:
    now = _now_iso()
    trajectory = dict(trajectory)
    trajectory["participant_id"] = normalize_participant_id(trajectory.get("participant_id", ""))
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            INSERT INTO narrative_trajectories
                (id, participant_id, title, before_text, turning_points, now_text,
                 preferred_story, evidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                before_text = excluded.before_text,
                turning_points = excluded.turning_points,
                now_text = excluded.now_text,
                preferred_story = excluded.preferred_story,
                evidence = excluded.evidence,
                updated_at = excluded.updated_at
            """,
            (
                trajectory["id"],
                trajectory["participant_id"],
                trajectory.get("title", "Narrative trajectory"),
                trajectory.get("before_text", ""),
                json.dumps(trajectory.get("turning_points", []), ensure_ascii=False),
                trajectory.get("now_text", ""),
                trajectory.get("preferred_story", ""),
                json.dumps(trajectory.get("evidence", []), ensure_ascii=False),
                trajectory.get("created_at") or now,
                now,
            ),
        )
        await db.commit()


async def list_narrative_trajectories(participant_id: str) -> List[Dict[str, Any]]:
    participant_id = normalize_participant_id(participant_id)
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM narrative_trajectories
               WHERE participant_id = ?
               ORDER BY updated_at DESC""",
            (participant_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["turning_points"] = json.loads(d.get("turning_points") or "[]")
                d["evidence"] = json.loads(d.get("evidence") or "[]")
                result.append(d)
            return result


async def get_story_card(participant_id: str) -> Optional[Dict[str, Any]]:
    participant_id = normalize_participant_id(participant_id)
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM participant_story_cards WHERE participant_id = ?",
            (participant_id,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_story_cards(participant_id: str) -> List[Dict[str, Any]]:
    participant_id = normalize_participant_id(participant_id)
    async with aiosqlite.connect(settings.database_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT id, participant_id, story_markdown, source_turn_count, created_at
               FROM participant_story_card_history
               WHERE participant_id = ?
               ORDER BY source_turn_count DESC, created_at DESC""",
            (participant_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def upsert_story_card(
    participant_id: str,
    story_markdown: str,
    source_turn_count: int,
) -> None:
    now = _now_iso()
    participant_id = normalize_participant_id(participant_id)
    async with aiosqlite.connect(settings.database_path) as db:
        await db.execute(
            """
            INSERT INTO participant_story_cards
                (participant_id, story_markdown, source_turn_count, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(participant_id) DO UPDATE SET
                story_markdown = excluded.story_markdown,
                source_turn_count = excluded.source_turn_count,
                updated_at = excluded.updated_at
            """,
            (participant_id, story_markdown, source_turn_count, now, now),
        )
        await db.execute(
            """
            INSERT INTO participant_story_card_history
                (id, participant_id, story_markdown, source_turn_count, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (str(uuid.uuid4()), participant_id, story_markdown, source_turn_count, now),
        )
        await db.commit()
