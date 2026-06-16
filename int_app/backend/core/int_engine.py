"""
INT Engine — orchestrates the four LLM calls that power each therapy turn.

Call order per turn:
  1. (conditional) select_stage   — advance to the next therapeutic stage
  2. plan_reflection              — choose a reflection level within the stage
  3. RAG retrieve                 — fetch exemplar questions from the knowledge base
  4. generate_response (stream)   — produce the therapist's reply
  5. check_goal                   — decide whether the current stage goal is met
"""

import datetime
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

import yaml

from ..config import settings
from .llm_client import llm_client
from .rag_engine import rag_engine
from .stages import (
    CRISIS_KEYWORDS,
    GOAL_CHECKER_PROMPTS,
    REFLECTION_DESCRIPTIONS,
    REFLECTION_LEVELS,
    REFLECTION_PLANNER_PROMPTS,
    RESPONSE_GEN_PROMPT,
    STAGE_DESCRIPTIONS,
    STAGE_DISPLAY_NAMES,
    STAGE_PLANNER_PROMPT,
    THERAPIST_PERSONA,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stage_key(stage: str) -> str:
    """Convert a stage name to a Python-identifier-safe key."""
    return stage.replace("-", "_").replace(" ", "_")


def _build_prompt_vars() -> Dict[str, str]:
    """Return a dict of all substitution variables used across prompt templates."""
    vars_: Dict[str, str] = {
        "persona": THERAPIST_PERSONA,
        "stage_trust_building": STAGE_DESCRIPTIONS["trust building"],
        "stage_problem_externalization": STAGE_DESCRIPTIONS["problem externalization"],
        "stage_re_authoring": STAGE_DESCRIPTIONS["re-authoring"],
        "stage_re_membering": STAGE_DESCRIPTIONS["re-membering"],
    }
    for key, desc in REFLECTION_DESCRIPTIONS.items():
        vars_[f"reflection_{key}"] = desc
    return vars_


def parse_yaml_field(text: str, field_name: str) -> str:
    """
    Extract *field_name* from a YAML block in *text*.

    Tries three strategies in order:
      1. Strip the ```yaml / ``` fences and parse with yaml.safe_load.
      2. Parse the raw text directly with yaml.safe_load.
      3. Regex fallback: look for ``field_name: <value>`` on a single line.

    Returns an empty string when the field cannot be found.
    """
    # Strategy 1 — extract content between ```yaml ... ``` (case-insensitive)
    fence_match = re.search(
        r"```(?:yaml|YAML)?\s*\n(.*?)\n```", text, re.DOTALL
    )
    candidate = fence_match.group(1) if fence_match else text

    for blob in (candidate, text):
        try:
            data = yaml.safe_load(blob)
            if isinstance(data, dict):
                # Try exact key first, then case-insensitive search
                if field_name in data:
                    return str(data[field_name]).strip()
                for k, v in data.items():
                    if str(k).lower() == field_name.lower():
                        return str(v).strip()
        except yaml.YAMLError:
            pass

    # Strategy 3 — regex fallback
    pattern = rf"(?:^|\n){re.escape(field_name)}\s*:\s*(.+)"
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"').strip("'")

    return ""


def build_history(turns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Convert stored turn dicts to the OpenAI messages format.
    Keeps at most the last 10 turns to stay within context limits.
    """
    messages: List[Dict[str, str]] = []
    for turn in turns[-10:]:
        messages.append({"role": "user", "content": turn.get("client", "")})
        messages.append({"role": "assistant", "content": turn.get("therapist", "")})
    return messages


def _history_summary(turns: List[Dict[str, Any]]) -> str:
    """Return a concise text summary of the last few turns for the stage planner."""
    if not turns:
        return "（暂无对话历史）"
    lines: List[str] = []
    for turn in turns[-5:]:
        lines.append(f"来访者：{turn.get('client', '')}")
        lines.append(f"咨询师：{turn.get('therapist', '')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Step 1 — Stage selection
# ---------------------------------------------------------------------------


async def select_stage(
    session_data: Dict[str, Any],
    user_input: str,
    history: List[Dict[str, str]],
) -> Tuple[str, str]:
    """
    Ask the stage-planner LLM which therapeutic stage to advance to.

    Returns ``(new_stage, draft_response)``.
    """
    vars_ = _build_prompt_vars()
    vars_["current_stage"] = session_data.get("stage", "trust building")
    vars_["history_summary"] = _history_summary(session_data.get("turns", []))

    system_prompt = STAGE_PLANNER_PROMPT.format(**vars_)

    raw: str = await llm_client.chat(
        system_prompt=system_prompt,
        user_message=user_input,
        model=settings.stage_planner_model,
        history=history,
        temperature=0.5,
    )

    stage = parse_yaml_field(raw, "Stage") or session_data.get("stage", "trust building")
    draft = parse_yaml_field(raw, "Response") or ""

    # Normalise stage name (the LLM might capitalise or add quotes)
    stage = stage.strip().lower()
    from .stages import STAGES
    if stage not in STAGES:
        stage = session_data.get("stage", "trust building")

    return stage, draft


# ---------------------------------------------------------------------------
# Step 2 — Reflection level selection
# ---------------------------------------------------------------------------


async def plan_reflection(
    session_data: Dict[str, Any],
    user_input: str,
    history: List[Dict[str, str]],
) -> Tuple[str, str]:
    """
    Ask the reflection-planner LLM which reflection level to use.

    Returns ``(reflection_level, draft_response)``.
    Falls back to the first reflection level of the current stage if parsing fails.
    """
    stage: str = session_data.get("stage", "trust building")
    template = REFLECTION_PLANNER_PROMPTS.get(stage, REFLECTION_PLANNER_PROMPTS["trust building"])

    vars_ = _build_prompt_vars()
    system_prompt = template.format(**vars_)

    raw: str = await llm_client.chat(
        system_prompt=system_prompt,
        user_message=user_input,
        model=settings.reflection_planner_model,
        history=history,
        temperature=0.5,
    )

    reflection_level = parse_yaml_field(raw, "Reflection_level") or ""
    draft = parse_yaml_field(raw, "Response") or ""

    # Validate; fall back to the first level for this stage
    valid_levels = REFLECTION_LEVELS.get(stage, [])
    if reflection_level not in valid_levels:
        reflection_level = valid_levels[0] if valid_levels else ""

    return reflection_level, draft


# ---------------------------------------------------------------------------
# Step 3 — Goal check
# ---------------------------------------------------------------------------


async def check_goal(
    session_data: Dict[str, Any],
    user_input: str,
    therapist_response: str,
    history: List[Dict[str, str]],
) -> bool:
    """
    Ask the goal-checker LLM whether the current stage goal has been met.

    Returns ``True`` when the LLM answers "Yes".
    """
    stage: str = session_data.get("stage", "trust building")
    template = GOAL_CHECKER_PROMPTS.get(stage, GOAL_CHECKER_PROMPTS["trust building"])

    vars_ = _build_prompt_vars()
    system_prompt = template.format(**vars_)

    # Include the most recent exchange so the checker has full context
    recent_history = list(history[-6:])  # last 3 turns
    recent_history.append({"role": "user", "content": user_input})
    recent_history.append({"role": "assistant", "content": therapist_response})

    raw: str = await llm_client.chat(
        system_prompt=system_prompt,
        user_message="请判断当前治疗阶段目标是否达成。",
        model=settings.goal_checker_model,
        history=recent_history,
        temperature=0.0,
        max_tokens=10,
    )

    return raw.strip().lower().startswith("yes")


# ---------------------------------------------------------------------------
# Step 4 — Streaming response generation
# ---------------------------------------------------------------------------


async def generate_response(
    session_data: Dict[str, Any],
    user_input: str,
    reflection_level: str,
    exemplars: List[str],
    draft: str,
    history: List[Dict[str, str]],
) -> AsyncGenerator[str, None]:
    """
    Stream the final therapist response token by token.

    Yields individual token strings.
    """
    stage: str = session_data.get("stage", "trust building")
    stage_display: str = STAGE_DISPLAY_NAMES.get(stage, stage)
    reflection_description: str = REFLECTION_DESCRIPTIONS.get(reflection_level, "")

    # Crisis detection — prepend a safety note to the exemplars section
    crisis_detected = any(kw in user_input for kw in CRISIS_KEYWORDS)
    if crisis_detected:
        safety_note = (
            "【危机提示】来访者提到了危机信号，请首先表达关心，"
            "并提供帮助热线：北京心理危机研究与干预中心 010-82951332 / "
            "全国心理援助热线 400-161-9995。\n"
        )
        exemplars_text = safety_note + "\n".join(exemplars)
    else:
        exemplars_text = "\n".join(exemplars) if exemplars else "（无检索结果）"

    vars_ = _build_prompt_vars()
    vars_.update(
        {
            "stage_display": stage_display,
            "reflection_level": reflection_level,
            "reflection_description": reflection_description,
            "exemplars": exemplars_text,
            "draft_response": draft or "（无草稿）",
            "user_input": user_input,
        }
    )

    system_prompt = RESPONSE_GEN_PROMPT.format(**vars_)

    stream = await llm_client.chat(
        system_prompt=system_prompt,
        user_message=user_input,
        model=settings.response_model,
        history=history,
        temperature=0.9,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


async def process_turn(
    session_data: Dict[str, Any],
    user_input: str,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Orchestrate a full therapy turn.

    Yields dicts of two shapes:
      - ``{"type": "token", "content": "<text>"}`` — streamed tokens
      - ``{"type": "done", "stage": ..., "reflection_level": ..., "session": ...}``
    """
    # Build conversation history in OpenAI message format
    history = build_history(session_data.get("turns", []))

    # ------------------------------------------------------------------
    # 1. Advance stage if the previous stage goal was accomplished and
    #    the stage has been active for at least 2 turns.
    # ------------------------------------------------------------------
    draft_response: str = ""
    if session_data.get("accomplish_goal") and session_data.get("stage_count", 0) >= 2:
        new_stage, stage_draft = await select_stage(session_data, user_input, history)
        session_data["stage"] = new_stage
        session_data["stage_count"] = 0
        session_data["accomplish_goal"] = False
        draft_response = stage_draft

    # ------------------------------------------------------------------
    # 2. Select reflection level within the current stage
    # ------------------------------------------------------------------
    reflection_level, reflection_draft = await plan_reflection(
        session_data, user_input, history
    )
    if not draft_response:
        draft_response = reflection_draft

    # ------------------------------------------------------------------
    # 3. RAG retrieval
    # ------------------------------------------------------------------
    exemplars: List[str] = await rag_engine.retrieve(
        user_input,
        session_data["stage"],
        reflection_level,
    )

    # ------------------------------------------------------------------
    # 4. Stream the final therapist response
    # ------------------------------------------------------------------
    full_response: str = ""
    async for token in generate_response(
        session_data, user_input, reflection_level, exemplars, draft_response, history
    ):
        yield {"type": "token", "content": token}
        full_response += token

    # ------------------------------------------------------------------
    # 5. Check whether the current stage goal is met (non-blocking from
    #    the user's perspective — the stream has already finished).
    # ------------------------------------------------------------------
    goal_achieved = await check_goal(
        session_data, user_input, full_response, history
    )

    # ------------------------------------------------------------------
    # 6. Build the turn record
    # ------------------------------------------------------------------
    turn: Dict[str, Any] = {
        "round": len(session_data.get("turns", [])) + 1,
        "client": user_input,
        "therapist": full_response,
        "stage": session_data["stage"],
        "reflection_level": reflection_level,
        "rag_references": exemplars,
        "user_cooperation": "",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
    }

    # ------------------------------------------------------------------
    # 7. Update session state in-place (caller persists to DB)
    # ------------------------------------------------------------------
    session_data.setdefault("turns", []).append(turn)
    session_data["stage_count"] = session_data.get("stage_count", 0) + 1
    if goal_achieved:
        session_data["accomplish_goal"] = True

    yield {
        "type": "done",
        "stage": session_data["stage"],
        "reflection_level": reflection_level,
        "session": session_data,
    }
