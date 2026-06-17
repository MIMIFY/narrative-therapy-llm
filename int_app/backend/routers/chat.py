import json
import uuid
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..database import create_session, get_session, update_session
from ..core.int_engine import process_turn

router = APIRouter(prefix="/api")


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
    session = await get_session(session_id)
    if not session:
        await create_session(session_id, req.participant_id)
        session = await get_session(session_id)

    if session is None:
        raise HTTPException(status_code=500, detail="Failed to initialise session")

    session_data = {
        "id": session["id"],
        "stage": session["stage"],
        "stage_count": session["stage_count"],
        "accomplish_goal": bool(session["accomplish_goal"]),
        "turns": json.loads(session["turns"]),
    }

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in process_turn(session_data, req.message, language=req.language):
                if event["type"] == "token":
                    payload = json.dumps(
                        {"token": event["content"], "done": False},
                        ensure_ascii=False,
                    )
                    yield f"data: {payload}\n\n"
                elif event["type"] == "done":
                    # Persist updated session to the database
                    updated = event["session"]
                    await update_session(
                        session_id,
                        updated["stage"],
                        updated["stage_count"],
                        1 if updated["accomplish_goal"] else 0,
                        json.dumps(updated["turns"], ensure_ascii=False),
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


@router.get("/session/{session_id}")
async def get_session_api(session_id: str):
    """Return the full session record including parsed turns."""
    session = await get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session["turns"] = json.loads(session["turns"])
    return session
