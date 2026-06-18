import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..database import append_session_turn, create_session, get_session, normalize_participant_id
from ..core.int_engine import process_turn

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str
    participant_id: str = ""
    language: str = "zh"


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    """
    Accept a user message and return a Server-Sent Events stream.

    Each SSE ``data:`` line contains a JSON object with one of:
      - ``{"token": "<text>", "done": false}`` — a streamed token
      - ``{"done": true, "session_id": "...", "stage": "...", "reflection_level": "..."}``
      - ``{"error": "<message>", "done": true}`` — on failure
    """
    # Resolve or create the session
    session_id = (req.session_id or "").strip() or str(uuid.uuid4())
    participant_id = normalize_participant_id(req.participant_id)
    session = await get_session(session_id)
    if not session:
        await create_session(session_id, participant_id)
        session = await get_session(session_id)

    if session is None:
        raise HTTPException(status_code=500, detail="Failed to initialise session")

    session_data = {
        "id": session["id"],
        "participant_id": session["participant_id"],
        "stage": session["stage"],
        "stage_count": session["stage_count"],
        "accomplish_goal": bool(session["accomplish_goal"]),
        "turns": json.loads(session["turns"]),
    }

    async def event_stream() -> AsyncGenerator[str, None]:
        streamed_text = ""
        attempted_round = len(session_data.get("turns", [])) + 1
        try:
            async for event in process_turn(session_data, req.message, language=req.language):
                if event["type"] == "token":
                    streamed_text += event["content"]
                    payload = json.dumps(
                        {"token": event["content"], "done": False},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
                elif event["type"] == "done":
                    # Persist updated session to the database
                    updated = event["session"]
                    await append_session_turn(
                        session_id,
                        updated["stage"],
                        updated["stage_count"],
                        1 if updated["accomplish_goal"] else 0,
                        updated["turns"][-1],
                    )
                    payload = json.dumps(
                        {
                            "done": True,
                            "session_id": session_id,
                            "stage": event["stage"],
                            "reflection_level": event["reflection_level"],
                        },
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming chat failed session=%s round=%s", session_id, attempted_round)
            await _persist_failed_turn(
                session_id=session_id,
                req=req,
                session_data=session_data,
                attempted_round=attempted_round,
                streamed_text=streamed_text,
                error_message=str(exc),
            )
            payload = json.dumps({"error": str(exc), "done": True})
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _persist_failed_turn(
    session_id: str,
    req: ChatRequest,
    session_data: dict,
    attempted_round: int,
    streamed_text: str,
    error_message: str,
) -> None:
    """Persist a failed/partial turn so user and researcher history stays auditable."""
    current = await get_session(session_id)
    if current is None:
        return

    turns = json.loads(current["turns"] or "[]")
    if len(turns) >= attempted_round:
        existing = turns[attempted_round - 1]
        if existing.get("client") == req.message:
            return

    turns.append(
        {
            "round": len(turns) + 1,
            "client": req.message,
            "therapist": streamed_text,
            "stage": session_data.get("stage", current["stage"]),
            "reflection_level": "",
            "rag_references": [],
            "user_cooperation": "",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace": {
                "error": {
                    "message": error_message,
                    "during": "chat_stream",
                },
                "runtime": {
                    "stream_failed": True,
                    "partial_response_chars": len(streamed_text),
                },
            },
        }
    )
    await append_session_turn(
        session_id,
        current["stage"],
        int(current["stage_count"] or 0),
        int(current["accomplish_goal"] or 0),
        turns[-1],
    )


@router.get("/session/{session_id}")
async def get_session_api(session_id: str):
    """Return the full session record including parsed turns."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["turns"] = json.loads(session["turns"])
    return session
