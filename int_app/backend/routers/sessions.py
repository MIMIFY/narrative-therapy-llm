import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyQuery, APIKeyHeader

from ..config import settings
from ..database import get_session, list_sessions

router = APIRouter(prefix="/api")

# Two ways to pass the admin key: query param or header
_query_scheme  = APIKeyQuery(name="admin_key", auto_error=False)
_header_scheme = APIKeyHeader(name="X-Admin-Key", auto_error=False)


async def require_admin(
    key_query: str  = Depends(_query_scheme),
    key_header: str = Depends(_header_scheme),
) -> None:
    provided = key_query or key_header
    if provided != settings.admin_key:
        raise HTTPException(status_code=401, detail="Invalid or missing admin key")


@router.get("/sessions")
async def list_all_sessions(
    _: None = Depends(require_admin),
) -> List[Dict[str, Any]]:
    """Return all sessions (admin only)."""
    return await list_sessions()


@router.get("/export/{session_id}")
async def export_session(session_id: str) -> JSONResponse:
    """
    Export a session's turns as a JSON file download.
    Compatible with IMCS_metrics.py input format.
    """
    session = await get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Not found"})

    turns: List[Dict[str, Any]] = json.loads(session["turns"])
    return JSONResponse(
        content=turns,
        headers={
            "Content-Disposition": f'attachment; filename="session_{session_id[:8]}.json"',
            "Content-Type": "application/json",
        },
    )
