"""Small pure helpers shared by the INT pipeline and tests."""

import re
from typing import Any, Dict, List, Optional

import yaml

CJK_RE = re.compile(r"[\u3400-\u9fff]")
LATIN_RE = re.compile(r"[A-Za-z]")


def resolve_response_language(user_input: str, requested_language: str = "zh") -> str:
    """Choose the response language from the user's message, falling back to UI language."""
    cjk_count = len(CJK_RE.findall(user_input))
    latin_count = len(LATIN_RE.findall(user_input))
    if cjk_count > 0 and cjk_count >= latin_count:
        return "zh"
    if latin_count > 0 and latin_count > cjk_count:
        return "en"
    return "en" if requested_language == "en" else "zh"


def parse_yaml_field(text: str, field_name: str) -> str:
    """
    Extract a field from a YAML-like LLM response.

    The planner prompts ask models to return short YAML blocks, but hosted
    models sometimes add fences, capitalization changes, or slightly malformed
    text. This helper keeps parsing tolerant while returning an empty string
    when the target field is unavailable.
    """
    fence_match = re.search(
        r"```(?:yaml|YAML)?\s*\n(.*?)\n```", text, re.DOTALL
    )
    candidate = fence_match.group(1) if fence_match else text

    for blob in (candidate, text):
        try:
            data = yaml.safe_load(blob)
            if isinstance(data, dict):
                if field_name in data:
                    return str(data[field_name]).strip()
                for key, value in data.items():
                    if str(key).lower() == field_name.lower():
                        return str(value).strip()
        except yaml.YAMLError:
            pass

    pattern = rf"(?:^|\n){re.escape(field_name)}\s*:\s*(.+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1).strip().strip('"').strip("'")

    return ""


def build_history(
    turns: List[Dict[str, Any]], max_turns: Optional[int] = 10
) -> List[Dict[str, str]]:
    """Convert stored turn dictionaries to OpenAI-compatible messages."""
    messages: List[Dict[str, str]] = []
    window = turns[-max_turns:] if max_turns else turns
    for turn in window:
        if turn.get("trace", {}).get("error"):
            messages.append({"role": "user", "content": turn.get("client", "")})
            continue
        messages.append({"role": "user", "content": turn.get("client", "")})
        messages.append({"role": "assistant", "content": turn.get("therapist", "")})
    return messages
