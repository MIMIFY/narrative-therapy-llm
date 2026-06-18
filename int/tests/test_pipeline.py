import sys
import os
import json

# Make sure the int package root is importable when running pytest from any cwd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from backend.core.stages import (
    STAGE_PLANNER_PROMPT,
    REFLECTION_PLANNER_PROMPTS,
    GOAL_CHECKER_PROMPTS,
    RESPONSE_GEN_PROMPT,
    REFLECTION_DESCRIPTIONS,
    STAGE_DESCRIPTIONS,
    THERAPIST_PERSONA,
    STAGE_DISPLAY_NAMES,
    STAGE_PAPER_NAMES,
    REFLECTION_LEVELS,
    REFLECTION_PAPER_NAMES,
    REFLECTION_RESPONSE_GUIDANCE,
    KNOWLEDGE_FILE_MAP,
    STAGE_RESPONSE_GUIDANCE,
    normalize_reflection_level,
    normalize_stage,
    reflection_to_paper_name,
    stage_to_paper_name,
)
from backend.routers.sessions import _turn_for_export
from backend.core.utils import build_history, parse_yaml_field, resolve_response_language
from backend.core.narrative_memory import _trajectory_from_memories
from backend.core.int_engine import (
    RAG_TOP_K,
    _adjust_reflection_for_flow,
    _build_rag_query,
    _derive_posture,
    _guard_stage_transition,
    _stage_transition_note,
    _should_force_next_stage,
    select_stage,
)
from backend.config import settings
from backend.database import (
    append_session_turn,
    create_session,
    get_session,
    init_db,
    update_session,
    update_turn_trace,
)


# ---------------------------------------------------------------------------
# parse_yaml_field
# ---------------------------------------------------------------------------


class TestParseYamlField:
    def test_yaml_fence_extraction(self):
        text = "some preamble\n```yaml\nStage: trust building\nResponse: hello\n```"
        assert parse_yaml_field(text, "Stage") == "trust building"
        assert parse_yaml_field(text, "Response") == "hello"

    def test_yaml_fence_uppercase(self):
        text = "```YAML\nReflection_level: 探索问题事件\n```"
        assert parse_yaml_field(text, "Reflection_level") == "探索问题事件"

    def test_raw_yaml_no_fence(self):
        text = "Stage: re-authoring\nResponse: 你好"
        assert parse_yaml_field(text, "Stage") == "re-authoring"

    def test_regex_fallback(self):
        # Deliberately malformed YAML that the parser cannot handle cleanly
        text = "Stage: trust building\nsome: [unclosed"
        assert parse_yaml_field(text, "Stage") == "trust building"

    def test_missing_field_returns_empty_string(self):
        text = "```yaml\nStage: trust building\n```"
        assert parse_yaml_field(text, "NonExistent") == ""

    def test_case_insensitive_key_match(self):
        text = "```yaml\nstage: re-membering\n```"
        assert parse_yaml_field(text, "Stage") == "re-membering"

    def test_quoted_value_stripped(self):
        text = 'Reflection_level: "共情安慰来访"'
        assert parse_yaml_field(text, "Reflection_level") == "共情安慰来访"


# ---------------------------------------------------------------------------
# build_history
# ---------------------------------------------------------------------------


class TestBuildHistory:
    def test_empty_turns(self):
        assert build_history([]) == []

    def test_single_turn_produces_two_messages(self):
        turns = [{"client": "你好", "therapist": "你好，有什么我可以帮你的？"}]
        messages = build_history(turns)
        assert messages == [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，有什么我可以帮你的？"},
        ]

    def test_truncated_to_last_10(self):
        turns = [{"client": f"msg{i}", "therapist": f"resp{i}"} for i in range(15)]
        messages = build_history(turns)
        # 10 turns × 2 messages each
        assert len(messages) == 20
        assert messages[0]["content"] == "msg5"

    def test_missing_keys_default_to_empty_string(self):
        turns = [{}]
        messages = build_history(turns)
        assert messages[0]["content"] == ""
        assert messages[1]["content"] == ""

    def test_failed_stream_turn_skips_partial_assistant_reply(self):
        turns = [
            {"client": "第一轮", "therapist": "完整回复"},
            {
                "client": "失败轮",
                "therapist": "半截回复",
                "trace": {"error": {"message": "stream failed"}},
            },
            {"client": "下一轮", "therapist": "继续回复"},
        ]
        messages = build_history(turns)
        assert messages == [
            {"role": "user", "content": "第一轮"},
            {"role": "assistant", "content": "完整回复"},
            {"role": "user", "content": "失败轮"},
            {"role": "user", "content": "下一轮"},
            {"role": "assistant", "content": "继续回复"},
        ]
        assert all(msg["content"] != "半截回复" for msg in messages)

    def test_preserves_order(self, fake_session_data):
        messages = build_history(fake_session_data["turns"])
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"


# ---------------------------------------------------------------------------
# resolve_response_language
# ---------------------------------------------------------------------------


class TestResolveResponseLanguage:
    def test_chinese_input_overrides_english_ui(self):
        assert resolve_response_language("我最近压力很大", "en") == "zh"

    def test_english_input_overrides_chinese_ui(self):
        assert resolve_response_language("I feel stuck lately", "zh") == "en"

    def test_falls_back_to_ui_language_for_ambiguous_input(self):
        assert resolve_response_language("1234", "en") == "en"
        assert resolve_response_language("1234", "zh") == "zh"


# ---------------------------------------------------------------------------
# Paper terminology and export mapping
# ---------------------------------------------------------------------------


class TestPaperTerminology:
    def test_all_internal_stages_have_paper_names(self):
        assert set(STAGE_PAPER_NAMES) == set(STAGE_DISPLAY_NAMES)

    def test_all_reflection_levels_have_paper_names(self):
        all_levels = {level for levels in REFLECTION_LEVELS.values() for level in levels}
        assert set(REFLECTION_PAPER_NAMES) == all_levels

    def test_all_stages_and_reflections_have_response_guidance(self):
        all_levels = {level for levels in REFLECTION_LEVELS.values() for level in levels}
        assert set(STAGE_RESPONSE_GUIDANCE) == set(STAGE_DISPLAY_NAMES)
        assert set(REFLECTION_RESPONSE_GUIDANCE) == all_levels
        assert all(STAGE_RESPONSE_GUIDANCE.values())
        assert all(REFLECTION_RESPONSE_GUIDANCE.values())

    def test_knowledge_map_uses_internal_rag_keys(self):
        for meta in KNOWLEDGE_FILE_MAP.values():
            assert meta["stage"] in REFLECTION_LEVELS
            assert meta["level"] in REFLECTION_LEVELS[meta["stage"]]

    def test_export_turn_uses_paper_english_names(self):
        exported = _turn_for_export(
            {
                "stage": "re-authoring",
                "reflection_level": "认同蓝图",
                "trace": {
                    "stage": {
                        "previous_stage": "problem externalization",
                        "current_stage": "re-authoring",
                        "raw_output": "Stage: problem externalization",
                    },
                    "reflection": {
                        "selected_level": "认同蓝图",
                        "raw_output": "Reflection_level: 认同蓝图",
                    },
                    "rag": {
                        "stage_filter": "re-authoring",
                        "reflection_filter": "认同蓝图",
                    },
                },
            }
        )

        assert exported["stage"] == "Re-authoring Conversation"
        assert exported["reflection_level"] == "Exploration of Identity Landscape"
        assert exported["trace"]["stage"]["previous_stage"] == "Problem Externalization"
        assert exported["trace"]["stage"]["current_stage"] == "Re-authoring Conversation"
        assert exported["trace"]["reflection"]["selected_level"] == "Exploration of Identity Landscape"
        assert exported["trace"]["stage"]["raw_output"] == "Stage: Problem Externalization"
        assert exported["trace"]["reflection"]["raw_output"] == "Reflection_level: Exploration of Identity Landscape"
        assert exported["trace"]["rag"]["stage_filter"] == "Re-authoring Conversation"
        assert exported["trace"]["rag"]["reflection_filter"] == "Exploration of Identity Landscape"

    def test_mapping_unknown_values_fall_back(self):
        assert stage_to_paper_name("unknown") == "unknown"
        assert reflection_to_paper_name("unknown") == "unknown"

    def test_stage_normalization_accepts_paper_terms(self):
        assert normalize_stage("Trust Building") == "trust building"
        assert normalize_stage("Re-authoring Conversation") == "re-authoring"
        assert normalize_stage("Reconnecting") == "re-membering"

    def test_stage_normalization_falls_back(self):
        assert normalize_stage("not-a-stage", fallback="problem externalization") == "problem externalization"
        assert normalize_stage("", fallback="bad") == "trust building"

    def test_reflection_normalization_accepts_paper_terms(self):
        assert (
            normalize_reflection_level("Exploration of Identity Landscape", "re-authoring")
            == "认同蓝图"
        )
        assert (
            normalize_reflection_level("Empathic Comforting", "trust building")
            == "共情安慰来访"
        )

    def test_reflection_normalization_falls_back_to_stage_first_level(self):
        assert normalize_reflection_level("bad", "problem externalization") == "隐喻命名问题"


# ---------------------------------------------------------------------------
# Prompt template completeness
# ---------------------------------------------------------------------------


def _all_dummy_vars():
    """Build a superset of dummy values covering every placeholder in every template."""
    vars_ = {
        "persona": THERAPIST_PERSONA,
        "stage_trust_building": STAGE_DESCRIPTIONS["trust building"],
        "stage_problem_externalization": STAGE_DESCRIPTIONS["problem externalization"],
        "stage_re_authoring": STAGE_DESCRIPTIONS["re-authoring"],
        "stage_re_membering": STAGE_DESCRIPTIONS["re-membering"],
        "current_stage": "trust building",
        "history_summary": "来访者：我很难过\n咨询师：能多说说吗",
        "stage_display": "建立信任",
        "reflection_level": "探索问题事件",
        "reflection_description": REFLECTION_DESCRIPTIONS["探索问题事件"],
        "stage_response_guidance": STAGE_RESPONSE_GUIDANCE["trust building"],
        "reflection_response_guidance": REFLECTION_RESPONSE_GUIDANCE["探索问题事件"],
        "exemplars": "示例问题1\n示例问题2",
        "draft_response": "草稿回复",
        "user_input": "我最近压力很大",
        "language_instruction": "请用自然流畅的中文回复。",
        "memory_context": "（暂无可用的长期记忆）",
        "stage_transition_note": "保持自然对话。",
    }
    for key, desc in REFLECTION_DESCRIPTIONS.items():
        vars_[f"reflection_{key}"] = desc
    return vars_


class TestPromptTemplates:
    def _fill(self, template: str, vars_: dict) -> str:
        return template.format(**vars_)

    def test_stage_planner_prompt(self):
        vars_ = _all_dummy_vars()
        result = self._fill(STAGE_PLANNER_PROMPT, vars_)
        assert len(result) > 0

    @pytest.mark.parametrize("stage", list(REFLECTION_PLANNER_PROMPTS.keys()))
    def test_reflection_planner_prompts(self, stage):
        vars_ = _all_dummy_vars()
        result = self._fill(REFLECTION_PLANNER_PROMPTS[stage], vars_)
        assert len(result) > 0

    @pytest.mark.parametrize("stage", list(GOAL_CHECKER_PROMPTS.keys()))
    def test_goal_checker_prompts(self, stage):
        vars_ = _all_dummy_vars()
        result = self._fill(GOAL_CHECKER_PROMPTS[stage], vars_)
        assert len(result) > 0

    def test_response_gen_prompt(self):
        vars_ = _all_dummy_vars()
        result = self._fill(RESPONSE_GEN_PROMPT, vars_)
        assert len(result) > 0


def test_trajectory_from_memories_requires_before_and_growth():
    assert _trajectory_from_memories("p1", []) is None
    trajectory = _trajectory_from_memories(
        "p1",
        [
            {
                "memory_type": "problem_narrative",
                "content": "用户提到审判官让自己害怕打开电脑。",
                "source_turn": 5,
                "source_session_id": "s1",
            },
            {
                "memory_type": "unique_outcome",
                "content": "用户发现自己害怕时也能发出一小步更新。",
                "source_turn": 10,
                "source_session_id": "s1",
            },
            {
                "memory_type": "preferred_identity",
                "content": "用户开始看见自己是在压力下仍想认真负责的人。",
                "source_turn": 15,
                "source_session_id": "s1",
            },
        ],
    )

    assert trajectory is not None
    assert trajectory["id"] == "p1:preferred-story-growth"
    assert "审判官" in trajectory["before_text"]
    assert len(trajectory["turning_points"]) == 2
    assert "认真负责" in trajectory["preferred_story"]


def test_rag_query_is_state_augmented():
    query = _build_rag_query("我刷不进去题", "problem externalization", "评估问题影响")
    assert "我刷不进去题" in query
    assert "problem externalization" in query
    assert "评估问题影响" in query
    assert RAG_TOP_K == 5


def test_user_pressure_can_force_next_stage():
    assert _should_force_next_stage(
        current_stage="problem externalization",
        planned_stage="problem externalization",
        user_input="你怎么一直问题外化我？不推进阶段",
        turns=[],
        goal_ready=True,
        threshold_ready=False,
    )


def test_reflection_avoids_renaming_after_metaphor_exists():
    level, note = _adjust_reflection_for_flow(
        "problem externalization",
        "隐喻命名问题",
        "我还是刷不进去",
        [{"client": "这像一只走路歪歪扭扭的企鹅"}],
    )
    assert level == "评估问题影响"
    assert "已有问题隐喻" in note


def test_reauthoring_action_focus_does_not_jump_to_remembering():
    stage, reason = _guard_stage_transition(
        current_stage="re-authoring",
        planned_stage="re-membering",
        user_input="我就是想知道我应该怎么做，怎么自发地开始刷题",
        turns=[],
        goal_ready=True,
        threshold_ready=True,
    )
    assert stage == "re-authoring"
    assert reason == "stayed_re_authoring_for_action_or_repair"


def test_remembering_rejection_routes_back_to_reauthoring():
    stage, reason = _guard_stage_transition(
        current_stage="re-membering",
        planned_stage="re-membering",
        user_input="我不想多聊她，这是我自己要面对的问题，我想知道怎么做",
        turns=[{"client": "楠楠是给过力量"}],
        goal_ready=False,
        threshold_ready=False,
    )
    assert stage == "re-authoring"
    assert reason == "corrected_back_to_re_authoring_for_action_focus"


def test_stage_transition_note_supports_action_focus_in_reauthoring():
    note = _stage_transition_note(
        current_stage="re-authoring",
        user_input="我想知道具体怎么开始行动，不要再绕关系了",
        turns=[],
        goal_ready=True,
        threshold_ready=True,
    )
    assert "停留在 re-authoring" in note
    assert "action landscape" in note


def test_stage_transition_note_routes_relationship_rejection_back_to_reauthoring():
    note = _stage_transition_note(
        current_stage="re-membering",
        user_input="我不想多聊她，这是我自己的问题，我想知道怎么做",
        turns=[],
        goal_ready=False,
        threshold_ready=False,
    )
    assert "回到 re-authoring" in note


def test_distress_or_frustration_uses_hold_posture():
    posture, reason = _derive_posture(
        stage="problem externalization",
        reflection_level="评估问题影响",
        user_input="你又开始重复我的话了，我真的很烦",
        turns=[],
    )
    assert posture == "hold"
    assert "distress" in reason


@pytest.mark.asyncio
async def test_select_stage_prompt_receives_dynamic_policy_note(monkeypatch):
    captured = {}

    async def fake_chat(**kwargs):
        captured["system_prompt"] = kwargs["system_prompt"]
        return "Stage: re-authoring"

    monkeypatch.setattr("backend.core.int_engine.llm_client.chat", fake_chat)
    session_data = {
        "stage": "problem externalization",
        "stage_transition_note": "来访者已经厌烦重复探索，请自然转向 re-authoring。",
        "turns": [],
    }

    stage, _, raw = await select_stage(session_data, "你怎么一直问影响，我想知道怎么办", [])

    assert stage == "re-authoring"
    assert raw == "Stage: re-authoring"
    assert "来访者已经厌烦重复探索" in captured["system_prompt"]


# ---------------------------------------------------------------------------
# Persistence safety
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_turn_trace_does_not_overwrite_newer_turns(tmp_path):
    original_db_path = settings.database_path
    settings.database_path = str(tmp_path / "int.sqlite3")
    try:
        await init_db()
        await create_session("trace-session", "participant-a")
        turns = [
            {"round": 1, "client": "one", "therapist": "reply one", "trace": {}},
            {"round": 2, "client": "two", "therapist": "reply two", "trace": {}},
        ]
        await update_session(
            "trace-session",
            "trust building",
            2,
            0,
            json.dumps(turns, ensure_ascii=False),
        )

        await update_turn_trace(
            "trace-session",
            1,
            {"goal_check": {"goal_achieved": True}},
            accomplish_goal=True,
        )

        row = await get_session("trace-session")
        saved_turns = json.loads(row["turns"])
        assert len(saved_turns) == 2
        assert saved_turns[0]["trace"]["goal_check"]["goal_achieved"] is True
        assert saved_turns[1]["client"] == "two"
        assert row["accomplish_goal"] == 1
    finally:
        settings.database_path = original_db_path


@pytest.mark.asyncio
async def test_append_session_turn_preserves_existing_trace(tmp_path):
    original_db_path = settings.database_path
    settings.database_path = str(tmp_path / "int.sqlite3")
    try:
        await init_db()
        await create_session("append-session", "participant-a")
        await append_session_turn(
            "append-session",
            "trust building",
            1,
            0,
            {"round": 1, "client": "one", "therapist": "reply one", "trace": {}},
        )
        await update_turn_trace(
            "append-session",
            1,
            {"goal_check": {"goal_achieved": False}},
        )
        await append_session_turn(
            "append-session",
            "trust building",
            2,
            0,
            {"round": 2, "client": "two", "therapist": "reply two", "trace": {}},
        )

        row = await get_session("append-session")
        saved_turns = json.loads(row["turns"])
        assert len(saved_turns) == 2
        assert saved_turns[0]["trace"]["goal_check"]["goal_achieved"] is False
        assert saved_turns[1]["client"] == "two"
    finally:
        settings.database_path = original_db_path


# ---------------------------------------------------------------------------
# Integration test — full pipeline against real API
# ---------------------------------------------------------------------------


@pytest.mark.slow
@pytest.mark.asyncio
async def test_process_turn_integration(fake_session_data):
    """Run one full process_turn() against the real API.

    Skipped in CI — run explicitly with: pytest -m slow
    """
    import copy
    from backend.core.int_engine import process_turn

    session = copy.deepcopy(fake_session_data)
    user_input = "我觉得自己什么事情都做不好，特别沮丧。"

    events = []
    async for event in process_turn(session, user_input, language="zh"):
        events.append(event)

    token_events = [e for e in events if e["type"] == "token"]
    done_events = [e for e in events if e["type"] == "done"]

    assert len(done_events) == 1, "Expected exactly one 'done' event"
    assert len(token_events) > 0, "Expected at least one token"

    done = done_events[0]
    assert done["stage"] in ["trust building", "problem externalization", "re-authoring", "re-membering"]
    assert done["reflection_level"] != ""
    assert len(done["session"]["turns"]) == len(fake_session_data["turns"]) + 1
