"""Narrative-therapy-specific long-term memory helpers."""

import json
import logging
import re
import uuid
from typing import Any, Dict, List

import chromadb

from ..config import settings
from ..database import (
    count_participant_turns,
    get_participant_sessions_full,
    get_session_summary,
    get_story_card,
    insert_participant_memory,
    list_story_cards,
    list_narrative_trajectories,
    list_participant_memories,
    upsert_narrative_trajectory,
    upsert_session_summary,
    upsert_story_card,
)
from ..database import normalize_participant_id
from .llm_client import llm_client
from .rag_engine import rag_engine

logger = logging.getLogger(__name__)

MEMORY_COLLECTION = "participant_narrative_memory"


def _extract_json_object(text: str) -> Dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1) if fenced else text
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start >= 0 and end > start:
        candidate = candidate[start : end + 1]
    return json.loads(candidate)


_chroma_client: Any | None = None
_chroma_collection: Any | None = None


def _memory_collection():
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        _chroma_client = chromadb.PersistentClient(path=settings.memory_chroma_db_path)
        _chroma_collection = _chroma_client.get_or_create_collection(
            name=MEMORY_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _chroma_collection


def _embed(text: str) -> List[float] | None:
    embed_model = getattr(rag_engine, "_embed_model", None)
    if embed_model is None:
        return None
    return embed_model.get_text_embedding(text)


async def retrieve_narrative_memories(
    participant_id: str,
    query: str,
    stage: str = "",
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Retrieve user-specific narrative memories with Chroma, falling back to SQLite."""
    participant_id = normalize_participant_id(participant_id)
    if not participant_id:
        return []

    embedding = _embed(query)
    if embedding is None:
        return await list_participant_memories(participant_id, limit=top_k)

    try:
        collection = _memory_collection()
        where: Dict[str, Any] = {"participant_id": participant_id}
        result = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        memories: List[Dict[str, Any]] = []
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for doc, meta, distance in zip(docs, metas, distances):
            if stage and meta.get("stage") not in ("", stage):
                continue
            memories.append(
                {
                    "id": meta.get("memory_id", ""),
                    "content": doc,
                    "memory_type": meta.get("memory_type", "observation"),
                    "stage": meta.get("stage", ""),
                    "confidence": meta.get("confidence", 0.7),
                    "distance": distance,
                }
            )
        return memories[:top_k]
    except Exception as exc:  # noqa: BLE001
        logger.warning("memory retrieval fell back to SQLite: %s", exc)
        return await list_participant_memories(participant_id, limit=top_k)


def format_memory_context(
    memories: List[Dict[str, Any]],
    trajectories: List[Dict[str, Any]],
    summary: Dict[str, Any] | None,
) -> str:
    """Render compact memory context for the response prompt."""
    lines: List[str] = []
    if summary and summary.get("summary"):
        lines.append("当前 session 摘要：")
        lines.append(f"- {summary['summary']}")
    if memories:
        lines.append("相关用户长期记忆：")
        for item in memories[:5]:
            lines.append(f"- [{item.get('memory_type', 'memory')}] {item.get('content', '')}")
    if trajectories:
        lines.append("叙事成长轨迹：")
        for traj in trajectories[:2]:
            before = traj.get("before_text", "")
            now = traj.get("now_text", "")
            preferred = traj.get("preferred_story", "")
            lines.append(
                f"- {traj.get('title', 'trajectory')}: 以前 {before}；现在 {now}；"
                f"正在形成的新故事：{preferred}"
            )
    return "\n".join(lines) if lines else "（暂无可用的长期记忆）"


def _first_memory_text(memories: List[Dict[str, Any]], types: set[str]) -> str:
    for item in sorted(memories, key=lambda x: int(x.get("source_turn") or 0)):
        if item.get("memory_type") in types and item.get("content"):
            return str(item["content"])
    return ""


def _trajectory_from_memories(participant_id: str, memories: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    """Build a conservative growth trajectory from structured memories."""
    before = _first_memory_text(memories, {"problem_narrative", "externalization"})
    turning_memories = [
        item
        for item in sorted(memories, key=lambda x: int(x.get("source_turn") or 0))
        if item.get("memory_type") in {"unique_outcome", "value", "preferred_identity", "important_relation"}
        and item.get("content")
    ]
    if not before or not turning_memories:
        return None

    turning_points = [str(item["content"]) for item in turning_memories[:4]]
    now = _first_memory_text(memories, {"preferred_identity", "value", "unique_outcome"})
    preferred = _first_memory_text(memories, {"value", "preferred_identity"})
    if not now:
        now = turning_points[-1]
    if not preferred:
        preferred = now

    evidence = [
        {
            "session_id": item.get("source_session_id", ""),
            "turn": int(item.get("source_turn") or 0),
            "memory_type": item.get("memory_type", ""),
        }
        for item in turning_memories[:6]
    ]
    return {
        "id": f"{participant_id}:preferred-story-growth",
        "participant_id": participant_id,
        "title": "从问题叙事到主动行动的成长轨迹",
        "before_text": before,
        "turning_points": turning_points,
        "now_text": now,
        "preferred_story": preferred,
        "evidence": evidence,
    }


async def ensure_narrative_trajectory(participant_id: str) -> Dict[str, Any] | None:
    """Create a trajectory when memories already show a before -> now movement."""
    existing = await list_narrative_trajectories(participant_id)
    memories = await list_participant_memories(participant_id, limit=100)
    trajectory = _trajectory_from_memories(participant_id, memories)
    if trajectory is None:
        return existing[0] if existing else None
    await upsert_narrative_trajectory(trajectory)
    return trajectory


async def build_narrative_memory_context(
    participant_id: str,
    session_id: str,
    query: str,
    stage: str,
) -> str:
    memories = await retrieve_narrative_memories(participant_id, query, stage=stage)
    trajectories = await list_narrative_trajectories(participant_id)
    summary = await get_session_summary(session_id)
    return format_memory_context(memories, trajectories, summary)


async def _index_memory(memory: Dict[str, Any]) -> None:
    embedding = _embed(memory["content"])
    if embedding is None:
        return
    collection = _memory_collection()
    collection.upsert(
        ids=[memory["id"]],
        embeddings=[embedding],
        documents=[memory["content"]],
        metadatas=[
            {
                "participant_id": memory["participant_id"],
                "memory_id": memory["id"],
                "memory_type": memory.get("memory_type", "observation"),
                "stage": memory.get("stage", ""),
                "confidence": float(memory.get("confidence", 0.7)),
                "source_session_id": memory.get("source_session_id", ""),
                "source_turn": int(memory.get("source_turn", 0)),
            }
        ],
    )


async def update_narrative_memory_after_turn(
    participant_id: str,
    session_id: str,
    turn: Dict[str, Any],
    trace: Dict[str, Any],
) -> None:
    """Extract structured narrative memory in the background after a turn."""
    if not participant_id:
        return

    existing_memories = await list_participant_memories(participant_id, limit=20)
    trajectories = await list_narrative_trajectories(participant_id)
    current_summary = await get_session_summary(session_id)

    system_prompt = """
你是 INT 叙事疗法系统的长期记忆更新器。你的任务不是诊断用户，而是从一轮对话中抽取对后续叙事疗法有帮助的记忆。

规则：
- 不要写医学诊断，不要把推测当事实。
- 使用“用户提到/表达/似乎在探索”等表述。
- 重点捕捉：问题叙事、问题外化命名、例外事件、价值观、重要关系、preferred identity、成长轨迹。
- 记忆要短、具体、可被后续对话检索。
- 当本轮或既有记忆中同时出现“以前的问题叙事/问题命名”和“现在的新理解、例外行动、价值或 preferred identity”时，必须写入 trajectory_updates。
- trajectory_updates 要表达一个连续变化：以前如何被问题影响；哪个具体转折显示了不同可能；现在如何重新理解自己；正在形成什么 preferred story。
- 如果没有值得长期保存的信息，返回空数组。

只输出 JSON：
{
  "new_memories": [
    {"memory_type": "problem_narrative|externalization|unique_outcome|value|important_relation|preferred_identity|risk_note|observation", "content": "...", "confidence": 0.0}
  ],
  "trajectory_updates": [
    {"title": "...", "before_text": "...", "turning_point": "...", "now_text": "...", "preferred_story": "..."}
  ],
  "session_summary": "...",
  "open_threads": ["..."]
}
"""

    payload = {
        "participant_id": participant_id,
        "session_id": session_id,
        "turn": turn,
        "trace_summary": trace,
        "existing_memories": existing_memories[:10],
        "existing_trajectories": trajectories[:5],
        "current_session_summary": current_summary,
    }
    raw = await llm_client.chat(
        system_prompt=system_prompt,
        user_message=json.dumps(payload, ensure_ascii=False),
        model=settings.goal_checker_model,
        temperature=0.1,
        max_tokens=1200,
    )

    try:
        data = _extract_json_object(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("memory extraction JSON parse failed: %s raw=%s", exc, raw[:500])
        return

    for item in data.get("new_memories", [])[:8]:
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        memory = {
            "id": str(uuid.uuid4()),
            "participant_id": participant_id,
            "memory_type": item.get("memory_type", "observation"),
            "content": content,
            "stage": turn.get("stage", ""),
            "confidence": float(item.get("confidence", 0.7)),
            "source_session_id": session_id,
            "source_turn": int(turn.get("round", 0)),
            "metadata": {"trace_stage": trace.get("stage", {})},
        }
        await insert_participant_memory(memory)
        await _index_memory(memory)

    for item in data.get("trajectory_updates", [])[:3]:
        title = str(item.get("title", "")).strip()
        if not title:
            continue
        trajectory_id = f"{participant_id}:{title.lower().replace(' ', '-')[:80]}"
        turning_point = str(item.get("turning_point", "")).strip()
        await upsert_narrative_trajectory(
            {
                "id": trajectory_id,
                "participant_id": participant_id,
                "title": title,
                "before_text": item.get("before_text", ""),
                "turning_points": [turning_point] if turning_point else [],
                "now_text": item.get("now_text", ""),
                "preferred_story": item.get("preferred_story", ""),
                "evidence": [{"session_id": session_id, "turn": turn.get("round", 0)}],
            }
        )

    await ensure_narrative_trajectory(participant_id)

    await upsert_session_summary(
        session_id=session_id,
        participant_id=participant_id,
        summary=str(data.get("session_summary", "")).strip(),
        open_threads=[str(x) for x in data.get("open_threads", [])[:8]],
        current_stage=turn.get("stage", ""),
    )


async def generate_story_card(participant_id: str, force: bool = False) -> Dict[str, Any]:
    """Generate or return a first-person positive narrative story card."""
    participant_id = normalize_participant_id(participant_id)
    turn_count = await count_participant_turns(participant_id)
    story_min_turns = max(1, int(settings.story_min_turns))
    if turn_count < story_min_turns and not force:
        return {
            "eligible": False,
            "turn_count": turn_count,
            "required_turns": story_min_turns,
            "remaining_turns": story_min_turns - turn_count,
            "story_markdown": "",
        }

    cached = await get_story_card(participant_id)
    if cached and cached.get("source_turn_count") == turn_count:
        return {
            "eligible": True,
            "turn_count": turn_count,
            "required_turns": story_min_turns,
            "remaining_turns": 0,
            "story_markdown": cached["story_markdown"],
            "history": await list_story_cards(participant_id),
            "cached": True,
        }

    sessions = await get_participant_sessions_full(participant_id)
    await ensure_narrative_trajectory(participant_id)
    memories = await list_participant_memories(participant_id, limit=80)
    trajectories = await list_narrative_trajectories(participant_id)

    compact_turns: List[Dict[str, Any]] = []
    for session in sessions:
        for turn in session.get("turns", []):
            compact_turns.append(
                {
                    "client": turn.get("client", ""),
                    "therapist": turn.get("therapist", ""),
                    "stage": turn.get("stage", ""),
                    "reflection_level": turn.get("reflection_level", ""),
                }
            )

    system_prompt = """
你是 INT 叙事疗法系统的“个人生命故事”撰写器。请基于用户长期对话、记忆与成长轨迹，写一张给用户看的第一人称正向故事卡。

要求：
- 第一人称“我”。
- 温暖、克制、真诚，不夸张，不鸡汤。
- 不要诊断，不要病理化。
- 呈现“以前的我/我逐渐看见/现在的我/我正在走向的故事”。
- 强调用户自己的价值、行动、关系、例外事件和成长路径。
- 用 Markdown 输出，包含一个标题和 4-6 个短段落。
- 不要暴露系统 trace、模型决策或内部术语。
"""
    payload = {
        "participant_id": participant_id,
        "turn_count": turn_count,
        "memories": memories,
        "trajectories": trajectories,
        "recent_turns": compact_turns[-80:],
    }
    story = await llm_client.chat(
        system_prompt=system_prompt,
        user_message=json.dumps(payload, ensure_ascii=False),
        model=settings.response_model,
        temperature=0.7,
        max_tokens=1200,
    )
    await upsert_story_card(participant_id, story, turn_count)
    return {
        "eligible": True,
        "turn_count": turn_count,
        "required_turns": story_min_turns,
        "remaining_turns": 0,
        "story_markdown": story,
        "history": await list_story_cards(participant_id),
        "cached": False,
    }
