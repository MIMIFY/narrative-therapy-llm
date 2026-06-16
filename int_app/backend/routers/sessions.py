import json
from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..database import get_session, list_sessions

router = APIRouter(prefix="/api")


@router.get("/sessions")
async def list_all_sessions() -> List[Dict[str, Any]]:
    """Return a summary list of all sessions."""
    return await list_sessions()


@router.get("/export/{session_id}")
async def export_session(session_id: str) -> JSONResponse:
    """
    Export a session's turns as a JSON file download.

    The exported format is compatible with ``IMCS_metrics.py``:
    a JSON array of turn objects.
    """
    session = await get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Not found"})

    turns: List[Dict[str, Any]] = json.loads(session["turns"])

    return JSONResponse(
        content=turns,
        headers={
            "Content-Disposition": (
                f'attachment; filename="session_{session_id[:8]}.json"'
            ),
            "Content-Type": "application/json",
        },
    )
