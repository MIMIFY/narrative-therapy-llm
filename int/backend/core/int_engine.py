"""
INT Engine — orchestrates the four LLM calls that power each therapy turn.

Call order per turn:
  1. (conditional) select_stage   — advance to the next therapeutic stage
  2. plan_reflection              — choose a reflection level within the stage
  3. RAG retrieve                 — fetch exemplar questions from the knowledge base
  4. generate_response (stream)   — produce the therapist's reply
  5. check_goal                   — decide whether the current stage goal is met
"""

import asyncio
import datetime
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

from ..config import settings
from .llm_client import llm_client
from .narrative_memory import (
    build_narrative_memory_context,
    update_narrative_memory_after_turn,
)
from .rag_engine import rag_engine
from ..database import update_turn_trace
from .stages import (
    CRISIS_KEYWORDS,
    GOAL_CHECKER_PROMPTS,
    POSTURE_INSTRUCTIONS,
    REFLECTION_DESCRIPTIONS,
    REFLECTION_PLANNER_PROMPTS,
    REFLECTION_RESPONSE_GUIDANCE,
    RESPONSE_GEN_PROMPT,
    STAGE_COUNT_THRESHOLDS,
    STAGE_DESCRIPTIONS,
    STAGE_DISPLAY_NAMES,
    STAGE_RESPONSE_GUIDANCE,
    STAGE_PLANNER_PROMPT,
    THERAPIST_PERSONA,
    normalize_reflection_level,
    normalize_stage,
)
from .utils import build_history, parse_yaml_field, resolve_response_language

logger = logging.getLogger(__name__)

RAG_TOP_K = 5
STAGE_ORDER = ["trust building", "problem externalization", "re-authoring", "re-membering"]

PROGRESSION_PRESSURE_KEYWORDS = [
    "一直问题外化",
    "不推进",
    "一直问",
    "一直追问",
    "别问",
    "不要再问",
    "不要再绕",
    "已经知道",
    "我知道影响",
    "改变不了",
    "难以改变",
    "很烦",
    "烦诶",
    "卡住",
]

ACTION_FOCUS_KEYWORDS = [
    "怎么做",
    "具体怎么",
    "我要怎么",
    "应该怎么",
    "怎么办",
    "如何",
    "如何开始",
    "自发",
    "自律",
    "行动",
    "开始",
    "第一步",
    "做事情",
    "该做啥做啥",
    "好好睡觉",
    "睡觉",
    "心流",
]

RELATIONSHIP_FOCUS_KEYWORDS = [
    "楠楠",
    "朋友",
    "家人",
    "父母",
    "妈妈",
    "爸爸",
    "伴侣",
    "关系",
    "支持",
    "陪伴",
    "重要的人",
    "指明灯",
]

RELATIONSHIP_REJECTION_KEYWORDS = [
    "不想聊",
    "不想多聊",
    "不想谈",
    "不想讨论",
    "不想提",
    "不想打扰",
    "鼓励对我没用",
    "这是我自己",
    "这是我的问题",
    "我问你",
    "我想要知道",
    "你还记得吗",
    "烦不烦",
    "一点用都没",
]

# Signal lists for rule-based flow control
_DISTRESS_SIGNALS = [
    "哭", "泪", "崩溃", "撑不住", "太难了", "很痛苦", "好痛苦",
    "绝望", "没有意义", "不想活", "受不了", "心好累",
    "好烦", "烦死了", "烦透了", "烦啊", "好累", "累死了",
    "没用", "一点用都没", "没有用", "放弃了", "不聊了", "不想聊",
    "你在重复", "又开始重复", "重复我的话",
]
_INSIGHT_SIGNALS = [
    "我明白了", "我意识到", "我发现", "我看见了",
    "我觉得我", "原来我", "其实我可以", "我想到",
    "也许我可以", "也许我不需要", "也许可以", "我觉得也许",
    "可以试试", "试试看", "我想试", "说不定",
    "我以为.*其实", "原来如此", "有道理",
]
ADVANCE_PRESSURE_KEYWORDS = [
    "一直问题外化", "不推进", "推进一下", "换个阶段",
    "不要一直", "能不能换", "往前走", "继续往前", "一直在问",
    "怎么一直在问", "能不能直接", "直接给我", "直接说",
]


@dataclass
class TurnTrace:
    turn_num: int
    stage: str
    stage_advanced: bool
    reflection_level: str
    rag_hits: list[str]
    goal_achieved: bool
    latency_ms: int

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


def _history_summary(turns: List[Dict[str, Any]]) -> str:
    """Return a concise text summary of the last few turns for the stage planner."""
    if not turns:
        return "（暂无对话历史）"
    lines: List[str] = []
    for turn in turns[-5:]:
        lines.append(f"来访者：{turn.get('client', '')}")
        lines.append(f"咨询师：{turn.get('therapist', '')}")
    return "\n".join(lines)


def _next_stage(stage: str) -> str:
    stage = normalize_stage(stage)
    try:
        idx = STAGE_ORDER.index(stage)
    except ValueError:
        return "trust building"
    return STAGE_ORDER[min(idx + 1, len(STAGE_ORDER) - 1)]


def _has_progression_pressure(user_input: str, turns: List[Dict[str, Any]]) -> bool:
    return any(keyword in user_input for keyword in PROGRESSION_PRESSURE_KEYWORDS)


def _wants_action_focus(user_input: str) -> bool:
    return any(keyword in user_input for keyword in ACTION_FOCUS_KEYWORDS)


def _has_relationship_focus(user_input: str, turns: List[Dict[str, Any]]) -> bool:
    recent_text = user_input + "\n" + "\n".join(
        str(turn.get("client", "")) for turn in turns[-2:]
    )
    return any(keyword in recent_text for keyword in RELATIONSHIP_FOCUS_KEYWORDS)


def _rejects_relationship_focus(user_input: str) -> bool:
    return any(keyword in user_input for keyword in RELATIONSHIP_REJECTION_KEYWORDS)


def _stage_transition_note(
    current_stage: str,
    user_input: str,
    turns: List[Dict[str, Any]],
    goal_ready: bool,
    threshold_ready: bool,
) -> str:
    if current_stage == "re-membering" and (
        _wants_action_focus(user_input) or _rejects_relationship_focus(user_input)
    ):
        return (
            "来访者正在拒绝关系探索或要求具体行动。请回到 re-authoring/action landscape，"
            "承认刚才偏离了Ta最关心的问题，并给出一个很小的下一步。"
        )
    if current_stage == "re-authoring" and _wants_action_focus(user_input):
        return (
            "来访者正在请求具体行动/自发性/自律。请停留在 re-authoring，优先使用 action landscape，"
            "不要转入 re-membering，除非来访者主动想谈重要关系。"
        )
    if _has_progression_pressure(user_input, turns):
        return (
            "来访者已经表达对重复探索的厌烦，或已经知道影响但想改变行为。"
            "请先修复关系并停止重复追问；只有在 problem externalization 卡住时才转入 re-authoring。"
        )
    if goal_ready and threshold_ready:
        return (
            f"当前阶段 {current_stage} 已多轮达标。若历史显示目标基本完成，"
            "请判断是否真的需要推进。re-authoring 不应因为刚出现行动线索就立刻进入 re-membering；"
            "re-membering 需要来访者愿意谈重要关系或支持资源。"
        )
    return "保持自然对话；只有在当前阶段目标基本完成且来访者准备好时才推进。"


def _should_force_next_stage(
    current_stage: str,
    planned_stage: str,
    user_input: str,
    turns: List[Dict[str, Any]],
    goal_ready: bool,
    threshold_ready: bool,
) -> bool:
    """Return True when the user explicitly signals they want to move past the current stage."""
    if not goal_ready:
        return False
    if planned_stage != current_stage:
        return False  # model is already planning to advance
    return any(sig in user_input for sig in ADVANCE_PRESSURE_KEYWORDS)


def _guard_stage_transition(
    current_stage: str,
    planned_stage: str,
    user_input: str,
    turns: List[Dict[str, Any]],
    goal_ready: bool,
    threshold_ready: bool,
) -> Tuple[str, str]:
    """Guard stage transitions to protect conversational flow.

    Returns (final_stage, reason). reason is empty string when no override was applied.
    The function may block a planned advance OR correct an ongoing bad-fit stage.
    """
    current_stage = normalize_stage(current_stage)
    planned_stage = normalize_stage(planned_stage, fallback=current_stage)

    # --- Guard 1: don't jump re-authoring → re-membering when user wants concrete action ---
    if current_stage == "re-authoring" and planned_stage == "re-membering":
        if any(sig in user_input for sig in ACTION_FOCUS_KEYWORDS):
            return "re-authoring", "stayed_re_authoring_for_action_or_repair"

    # --- Guard 2: escape re-membering when user rejects relationship focus ---
    if current_stage == "re-membering":
        has_rejection = any(sig in user_input for sig in RELATIONSHIP_REJECTION_KEYWORDS)
        has_action = any(sig in user_input for sig in ACTION_FOCUS_KEYWORDS)
        if has_rejection or (has_action and not goal_ready):
            return "re-authoring", "corrected_back_to_re_authoring_for_action_focus"

    return planned_stage, ""


def _adjust_reflection_for_flow(
    stage: str,
    reflection_level: str,
    user_input: str,
    turns: List[Dict[str, Any]],
) -> Tuple[str, str]:
    """Apply rule-based adjustments to avoid re-doing work the user already accomplished.

    Returns (adjusted_level, note). note is empty string when no adjustment was made.
    """
    if stage == "problem externalization" and reflection_level == "隐喻命名问题":
        # If user has already named a metaphor in recent turns, skip naming
        recent_client = " ".join(t.get("client", "") for t in turns[-5:])
        if "像" in recent_client or "比如" in recent_client:
            return "评估问题影响", "已有问题隐喻，跳过命名直接评估影响"
    return reflection_level, ""


def _build_rag_query(user_input: str, stage: str, reflection_level: str) -> str:
    """Build a state-augmented RAG query (paper §3.2.3 E_t = RAG(C_t, s_t, l_t))."""
    return f"{user_input} [{stage}] [{reflection_level}]"


def _derive_posture(
    stage: str,
    reflection_level: str,
    user_input: str,
    turns: List[Dict[str, Any]],
) -> Tuple[str, str]:
    """Determine therapist response posture without an LLM call.

    Returns (posture, reason) where posture is one of: hold | explore | advance.
    """
    if any(kw in user_input for kw in _DISTRESS_SIGNALS):
        return "hold", "user showing distress, frustration, or rejection"
    if stage in ("re-authoring", "re-membering") and any(kw in user_input for kw in _INSIGHT_SIGNALS):
        return "advance", "user showing insight"
    return "explore", "default exploration"


# ---------------------------------------------------------------------------
# Step 1 — Stage selection
# ---------------------------------------------------------------------------


async def select_stage(
    session_data: Dict[str, Any],
    user_input: str,
    history: List[Dict[str, str]],
) -> Tuple[str, str, str]:
    """
    Ask the stage-planner LLM which therapeutic stage to advance to.

    Returns ``(new_stage, draft_response)``.
    """
    vars_ = _build_prompt_vars()
    vars_["current_stage"] = session_data.get("stage", "trust building")
    vars_["history_summary"] = _history_summary(session_data.get("turns", []))
    vars_["stage_transition_note"] = session_data.get(
        "stage_transition_note",
        "保持自然对话；只有在当前阶段目标基本完成且来访者准备好时才推进。",
    )

    system_prompt = STAGE_PLANNER_PROMPT.format(**vars_)

    raw: str = await llm_client.chat(
        system_prompt=system_prompt,
        user_message=user_input,
        model=settings.stage_planner_model,
        history=history,
        temperature=0.5,
    )

    previous_stage = session_data.get("stage", "trust building")
    stage = normalize_stage(parse_yaml_field(raw, "Stage"), fallback=previous_stage)
    return stage, "", raw


# ---------------------------------------------------------------------------
# Step 2 — Reflection level selection
# ---------------------------------------------------------------------------


async def plan_reflection(
    session_data: Dict[str, Any],
    user_input: str,
    history: List[Dict[str, str]],
) -> Tuple[str, str, str]:
    """
    Ask the reflection-planner LLM which reflection level to use.

    Returns ``(reflection_level, draft_response)``.
    Falls back to the first reflection level of the current stage if parsing fails.
    """
    stage: str = normalize_stage(session_data.get("stage", "trust building"))
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

    reflection_level = normalize_reflection_level(parse_yaml_field(raw, "Reflection_level"), stage)
    return reflection_level, "", raw


# ---------------------------------------------------------------------------
# Step 3 — Goal check
# ---------------------------------------------------------------------------


async def check_goal(
    session_data: Dict[str, Any],
    user_input: str,
    therapist_response: str,
    history: List[Dict[str, str]],
) -> Tuple[bool, str]:
    """
    Ask the goal-checker LLM whether the current stage goal has been met.

    Returns ``True`` when the LLM answers "Yes".
    """
    stage: str = normalize_stage(session_data.get("stage", "trust building"))
    template = GOAL_CHECKER_PROMPTS.get(stage, GOAL_CHECKER_PROMPTS["trust building"])

    vars_ = _build_prompt_vars()
    system_prompt = template.format(**vars_)

    # Dify uses stage-specific windows: trust_building=3 turns, others=4 turns
    window_msgs = 6 if stage == "trust building" else 8
    recent_history = list(history[-window_msgs:])
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

    return raw.strip().lower().startswith("yes"), raw


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
    language: str = "zh",
    memory_context: str = "（暂无可用的长期记忆）",
    stage_transition_note: str = "",
    posture_instruction: str = "",
) -> AsyncGenerator[str, None]:
    """
    Stream the final therapist response token by token.

    Yields individual token strings.
    """
    stage: str = normalize_stage(session_data.get("stage", "trust building"))
    stage_display: str = STAGE_DISPLAY_NAMES.get(stage, stage)
    stage_response_guidance: str = STAGE_RESPONSE_GUIDANCE.get(stage, "")
    reflection_response_guidance: str = REFLECTION_RESPONSE_GUIDANCE.get(reflection_level, "")

    # Crisis detection — prepend a safety note to the exemplars section
    response_language = resolve_response_language(user_input, language)
    crisis_detected = any(kw in user_input for kw in CRISIS_KEYWORDS)
    if crisis_detected:
        if response_language == "en":
            safety_note = (
                "[Crisis note] The client mentioned a crisis signal. First express care. "
                "If they may be in immediate danger, encourage them to contact local emergency services. "
                "If they are in the US or Canada, they can call or text 988 for crisis support.\n"
            )
        else:
            safety_note = (
                "【危机提示】来访者提到了危机信号，请首先表达关心，"
                "并提供帮助热线：北京心理危机研究与干预中心 010-82951332 / "
                "全国心理援助热线 400-161-9995。\n"
            )
        exemplars_text = safety_note + "\n".join(exemplars)
    else:
        exemplars_text = "\n".join(exemplars) if exemplars else "（无检索结果）"

    if response_language == "en":
        lang_instruction = (
            "## Language Requirement:\n"
            "The client is communicating in English. You MUST reply in English only. "
            "Keep the same warm, natural, and empathetic tone. Use culturally natural phrasing "
            "for an English-speaking user, avoid literal translation from Chinese, and keep the reply concise."
        )
    else:
        lang_instruction = (
            "## 语言要求：\n"
            "请用自然流畅的中文回复，贴近中文语境下的表达习惯，避免生硬翻译腔。"
        )

    vars_ = _build_prompt_vars()
    vars_.update(
        {
            "stage_display": stage_display,
            "reflection_level": reflection_level,
            "stage_response_guidance": stage_response_guidance,
            "reflection_response_guidance": reflection_response_guidance,
            "exemplars": exemplars_text,
            "draft_response": draft or "（无草稿）",
            "memory_context": memory_context,
            "user_input": user_input,
            "language_instruction": lang_instruction,
            "stage_transition_note": stage_transition_note,
        }
    )

    system_prompt = RESPONSE_GEN_PROMPT.format(**vars_)

    # Inject posture instruction after template formatting (not a template variable)
    if posture_instruction:
        system_prompt += f"\n\n## 本轮回应姿态（必须遵守）：\n{posture_instruction}"

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
    language: str = "zh",
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Orchestrate a full therapy turn.

    Yields dicts of two shapes:
      - ``{"type": "token", "content": "<text>"}`` — streamed tokens
      - ``{"type": "done", "stage": ..., "reflection_level": ..., "session": ...}``
    """
    _t0 = time.monotonic()
    turns = session_data.get("turns", [])
    session_data["stage"] = normalize_stage(session_data.get("stage", "trust building"))

    draft_response: str = ""
    stage_raw: str = ""
    reflection_raw: str = ""
    stage_advanced = False
    transition_reason: str = ""

    threshold = STAGE_COUNT_THRESHOLDS.get(
        session_data.get("stage", "trust building"),
        max(STAGE_COUNT_THRESHOLDS.values()),
    )
    threshold_ready = session_data.get("stage_count", 0) >= threshold
    goal_ready = bool(session_data.get("accomplish_goal"))
    stage_policy_note = _stage_transition_note(
        current_stage=session_data["stage"],
        user_input=user_input,
        turns=turns,
        goal_ready=goal_ready,
        threshold_ready=threshold_ready,
    )
    session_data["stage_transition_note"] = stage_policy_note

    # ---- Determine planned next stage ----
    normal_advance = goal_ready and threshold_ready
    force_advance = not normal_advance and _should_force_next_stage(
        current_stage=session_data["stage"],
        planned_stage=session_data["stage"],
        user_input=user_input,
        turns=turns,
        goal_ready=goal_ready,
        threshold_ready=threshold_ready,
    )
    if normal_advance or force_advance:
        history_stage = build_history(turns, max_turns=10)
        planned_stage, stage_draft, stage_raw = await select_stage(session_data, user_input, history_stage)
        draft_response = stage_draft
    else:
        planned_stage = session_data["stage"]

    # ---- Guard the transition (called every turn, pure Python) ----
    guarded_stage, transition_reason = _guard_stage_transition(
        current_stage=session_data["stage"],
        planned_stage=planned_stage,
        user_input=user_input,
        turns=turns,
        goal_ready=goal_ready,
        threshold_ready=threshold_ready,
    )
    if guarded_stage != session_data["stage"]:
        stage_advanced = True
        session_data["stage"] = guarded_stage
        session_data["stage_count"] = 0
        session_data["accomplish_goal"] = False
        if not stage_raw and transition_reason:
            stage_raw = f"[guard: {transition_reason}]"

    # ---- Select reflection level ----
    history_reflection = build_history(turns, max_turns=5)
    reflection_level, reflection_draft, reflection_raw = await plan_reflection(
        session_data, user_input, history_reflection
    )
    if not draft_response:
        draft_response = reflection_draft

    # ---- Adjust reflection for flow (rule-based, no LLM) ----
    reflection_level, flow_note = _adjust_reflection_for_flow(
        session_data["stage"], reflection_level, user_input, turns
    )

    # ---- Derive response posture (rule-based, no LLM) ----
    posture, posture_reason = _derive_posture(
        session_data["stage"], reflection_level, user_input, turns
    )
    posture_instr = POSTURE_INSTRUCTIONS[posture]

    # ---- Stage transition note for prompt ----
    stage_transition_note = stage_policy_note
    if stage_advanced:
        _sd = STAGE_DISPLAY_NAMES.get(session_data["stage"], session_data["stage"])
        stage_transition_note = (
            f"（当前已自然进入 **{_sd}** 新阶段，请用一句话自然衔接，"
            "无需明说“进入新阶段”，顺着来访者刚才的话继续。）\n"
            f"{stage_policy_note}"
        )

    # ---- RAG retrieval with state-augmented query ----
    rag_query = _build_rag_query(user_input, session_data["stage"], reflection_level)
    exemplars: List[str] = await rag_engine.retrieve(
        rag_query, session_data["stage"], reflection_level, top_k=RAG_TOP_K
    )

    participant_id = session_data.get("participant_id", "")
    memory_context = await build_narrative_memory_context(
        participant_id=participant_id,
        session_id=session_data.get("id", ""),
        query=user_input,
        stage=session_data["stage"],
    )

    # ---- Stream response ----
    history_response = build_history(turns, max_turns=50)
    full_response: str = ""
    async for token in generate_response(
        session_data, user_input, reflection_level, exemplars, draft_response,
        history_response, language=language, memory_context=memory_context,
        stage_transition_note=stage_transition_note,
        posture_instruction=posture_instr,
    ):
        yield {"type": "token", "content": token}
        full_response += token

    # ------------------------------------------------------------------
    # Build the turn record and update session state before yielding
    # "done", so the caller can persist immediately without waiting for
    # goal checking.
    # ------------------------------------------------------------------
    trace: Dict[str, Any] = {
        "stage": {
            "previous_stage": turns[-1].get("stage") if turns else "trust building",
            "current_stage": session_data["stage"],
            "stage_advanced": stage_advanced,
            "transition_reason": transition_reason,
            "policy_note": stage_policy_note,
            "raw_output": stage_raw,
            "draft_response": draft_response if stage_raw else "",
        },
        "reflection": {
            "raw_output": reflection_raw,
            "selected_level": reflection_level,
            "draft_response": reflection_draft,
            "posture": posture,
            "posture_reason": posture_reason,
            "flow_note": flow_note,
        },
        "rag": {
            "query": rag_query,
            "stage_filter": session_data["stage"],
            "reflection_filter": reflection_level,
            "top_k": RAG_TOP_K,
            "hits": exemplars,
        },
        "memory": {
            "context": memory_context,
            "update_interval": max(1, int(settings.memory_update_interval)),
            "update_scheduled": False,
        },
        "runtime": {
            "model_names": {
                "stage_planner": settings.stage_planner_model,
                "reflection_planner": settings.reflection_planner_model,
                "response": settings.response_model,
                "goal_checker": settings.goal_checker_model,
            }
        },
    }

    turn: Dict[str, Any] = {
        "round": len(session_data.get("turns", [])) + 1,
        "client": user_input,
        "therapist": full_response,
        "stage": session_data["stage"],
        "reflection_level": reflection_level,
        "rag_references": exemplars,
        "user_cooperation": "",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "trace": trace,
    }

    session_data.setdefault("turns", []).append(turn)
    session_data["stage_count"] = session_data.get("stage_count", 0) + 1

    yield {
        "type": "done",
        "stage": session_data["stage"],
        "reflection_level": reflection_level,
        "session": session_data,
    }

    # ------------------------------------------------------------------
    # 6. Goal check runs after the "done" event so it never blocks the
    #    response stream. The result is applied on the NEXT turn via the
    #    session state that the background task writes to the DB directly.
    # ------------------------------------------------------------------
    latency_ms = int((time.monotonic() - _t0) * 1000)
    session_id: str = session_data.get("id", "")

    async def _bg_goal_check() -> None:
        try:
            goal_achieved, goal_raw = await check_goal(
                session_data, user_input, full_response, history_response
            )
            trace["goal_check"] = {
                "raw_output": goal_raw,
                "goal_achieved": goal_achieved,
            }
            trace["runtime"]["latency_ms"] = latency_ms
            memory_interval = max(1, int(settings.memory_update_interval))
            should_update_memory = (
                bool(participant_id)
                and int(turn.get("round", 0)) >= memory_interval
                and int(turn.get("round", 0)) % memory_interval == 0
            )
            trace["memory"]["update_scheduled"] = should_update_memory
            if should_update_memory:
                await update_narrative_memory_after_turn(
                    participant_id=participant_id,
                    session_id=session_id,
                    turn=turn,
                    trace=trace,
                )
            if goal_achieved:
                session_data["accomplish_goal"] = True
            await update_turn_trace(
                session_id=session_id,
                turn_round=int(turn.get("round", 0)),
                trace=trace,
                accomplish_goal=True if goal_achieved else None,
            )

            logger.info(
                "[INT-TRACE] %s",
                json.dumps(
                    {
                        "turn": len(session_data["turns"]),
                        "stage": session_data["stage"],
                        "stage_advanced": stage_advanced,
                        "reflection_level": reflection_level,
                        "rag_hits": len(exemplars),
                        "goal_achieved": goal_achieved,
                        "latency_ms": latency_ms,
                    },
                    ensure_ascii=False,
                ),
            )
        except Exception as exc:
            logger.error(
                "[INT-TRACE] _bg_goal_check failed session=%s: %s",
                session_id,
                exc,
                exc_info=True,
            )

    _goal_task = asyncio.create_task(_bg_goal_check())
    _goal_task.add_done_callback(lambda t: None)
