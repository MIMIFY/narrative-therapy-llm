import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response
from fastapi.security import APIKeyQuery, APIKeyHeader

from ..config import settings
from ..database import get_session, list_sessions, list_sessions_by_participant
from ..database import list_story_cards
from ..core.narrative_memory import generate_story_card
from ..core.stages import (
    REFLECTION_PAPER_NAMES,
    STAGE_PAPER_NAMES,
    reflection_to_paper_name,
    stage_to_paper_name,
)

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


@router.get("/participant/{participant_id}/sessions")
async def list_participant_sessions(participant_id: str) -> List[Dict[str, Any]]:
    """Return session summaries for one participant ID."""
    return await list_sessions_by_participant(participant_id)


@router.post("/participant/{participant_id}/story")
async def participant_story(participant_id: str) -> Dict[str, Any]:
    """Generate or return a first-person narrative story card for a participant."""
    return await generate_story_card(participant_id)


@router.get("/participant/{participant_id}/stories")
async def participant_story_history(participant_id: str) -> List[Dict[str, Any]]:
    """Return all generated story card versions for one participant."""
    return await list_story_cards(participant_id)


@router.get("/export/{session_id}")
async def export_session(session_id: str) -> Response:
    """
    Export a session's turns as a JSON file download.
    Compatible with IMCS_metrics.py input format.
    """
    session = await get_session(session_id)
    if not session:
        return JSONResponse(status_code=404, content={"error": "Not found"})

    turns: List[Dict[str, Any]] = [
        _turn_for_export(turn) for turn in json.loads(session["turns"])
    ]
    body = json.dumps(turns, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="session_{session_id[:8]}.json"',
        },
    )


def _turn_for_export(turn: Dict[str, Any]) -> Dict[str, Any]:
    exported = dict(turn)
    if "stage" in exported:
        exported["stage"] = stage_to_paper_name(str(exported["stage"]))
    if "reflection_level" in exported:
        exported["reflection_level"] = reflection_to_paper_name(str(exported["reflection_level"]))

    trace = exported.get("trace")
    if isinstance(trace, dict):
        exported["trace"] = _trace_for_export(trace)
    return exported


def _trace_for_export(trace: Dict[str, Any]) -> Dict[str, Any]:
    exported = dict(trace)
    stage_trace = exported.get("stage")
    if isinstance(stage_trace, dict):
        stage_trace = dict(stage_trace)
        for key in ("previous_stage", "current_stage"):
            if key in stage_trace:
                stage_trace[key] = stage_to_paper_name(str(stage_trace[key]))
        if "raw_output" in stage_trace:
            stage_trace["raw_output"] = _replace_paper_terms(str(stage_trace["raw_output"]))
        exported["stage"] = stage_trace

    reflection_trace = exported.get("reflection")
    if isinstance(reflection_trace, dict):
        reflection_trace = dict(reflection_trace)
        if "selected_level" in reflection_trace:
            reflection_trace["selected_level"] = reflection_to_paper_name(
                str(reflection_trace["selected_level"])
            )
        if "raw_output" in reflection_trace:
            reflection_trace["raw_output"] = _replace_paper_terms(
                str(reflection_trace["raw_output"])
            )
        exported["reflection"] = reflection_trace

    rag_trace = exported.get("rag")
    if isinstance(rag_trace, dict):
        rag_trace = dict(rag_trace)
        if "stage_filter" in rag_trace:
            rag_trace["stage_filter"] = stage_to_paper_name(str(rag_trace["stage_filter"]))
        if "reflection_filter" in rag_trace:
            rag_trace["reflection_filter"] = reflection_to_paper_name(
                str(rag_trace["reflection_filter"])
            )
        exported["rag"] = rag_trace

    return exported


def _replace_paper_terms(text: str) -> str:
    for internal, paper_name in {**STAGE_PAPER_NAMES, **REFLECTION_PAPER_NAMES}.items():
        text = text.replace(internal, paper_name)
    return text
