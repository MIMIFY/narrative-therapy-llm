"""
Simulate ESConv client profiles interacting with the INT system.

Input: ESConv.json (1300 client profiles with emotion, problem, situation, dialog history)
Output: JSON files with full INT dialogue (client + therapist + stage + reflection per turn)

Usage:
    # Run first 10 profiles
    python simulate_client.py --max-profiles 10 --turns 35

    # Single profile by index
    python simulate_client.py --profile-index 42 --turns 35

    # Custom settings
    python simulate_client.py --max-profiles 50 --turns 50 --language zh \
        --cooperation-level 1 --client-model google/gemini-2.5-flash

    # Specify ESConv.json path explicitly
    python simulate_client.py --esconv ../data/esconv_profiles/ESConv.json --max-profiles 5
"""

import argparse
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from openai import OpenAI


COOPERATION_LEVELS = {
    0: "uncooperative — resistant, deflecting, giving minimal answers, sometimes hostile",
    1: "slightly resistant — reluctant to share, brief responses, avoids depth",
    2: "moderately cooperative — engages but stays surface-level, occasional openness",
    3: "cooperative — willing to explore, provides details, responds to therapist direction",
    4: "highly cooperative — deeply engaged, shares openly, reflects actively",
}

CLIENT_SYSTEM_PROMPT_EN = """You are role-playing as a therapy client seeking help. You must stay in character throughout the conversation.

## Your Profile
- Emotion: {emotion_type}
- Problem: {problem_type}
- Situation: {situation}
- Personality: {personality}
- What you've said before: {seeker_background}

## Your Cooperation Level: {cooperation_level} ({cooperation_desc})

## Rules
1. Respond naturally as this person would in a real therapy session. Match the personality traits above.
2. Match the cooperation level — if uncooperative, be brief/resistant; if cooperative, share more.
3. Do NOT break character or mention you are an AI.
4. Keep responses concise (1-3 sentences typically, max 50 words).
5. Show realistic emotional responses — frustration, sadness, hope, resistance, breakthroughs.
6. Do NOT be overly compliant or formulaic. Real clients sometimes go off-topic, push back, or express impatience.
7. Respond to what the therapist actually said — don't just continue a monologue.
8. As the conversation progresses, you may gradually open up (or not, depending on cooperation level).

Respond only with your next message as the client. No quotes, no labels, no explanation."""

CLIENT_SYSTEM_PROMPT_ZH = """你正在扮演一个寻求帮助的来访者。你必须全程保持角色。

## 你的人设
- 情绪: {emotion_type}
- 问题: {problem_type}
- 情境: {situation}
- 性格特点: {personality}
- 你之前说过的话: {seeker_background}

## 你的配合程度: {cooperation_level} ({cooperation_desc})

## 规则
1. 像真实来访者一样自然地回应，符合上面的性格特点。
2. 匹配配合程度——如果不配合就简短/抗拒；如果配合就多分享。
3. 不要跳出角色或提到你是AI。
4. 回复简洁（通常1-3句话，不超过30字）。
5. 表现真实的情绪反应——烦躁、悲伤、希望、抗拒、突破。
6. 不要过度配合或公式化。真实来访者有时会跑题、反驳或表达不耐烦。
7. 回应咨询师实际说的内容——不要自顾自独白。
8. 随着对话推进，你可能会逐渐打开（也可能不会，取决于配合程度）。

只输出你作为来访者的下一条消息。不要引号、标签或解释。"""


def _infer_personality(seeker_lines: List[str]) -> str:
    """Infer a brief personality sketch from seeker utterances."""
    if not seeker_lines:
        return ""

    total_chars = sum(len(line) for line in seeker_lines)
    avg_len = total_chars / len(seeker_lines)
    num_questions = sum(1 for line in seeker_lines if "?" in line)
    num_exclamations = sum(1 for line in seeker_lines if "!" in line)
    all_text = " ".join(seeker_lines).lower()

    traits = []

    # Length-based: terse vs verbose
    if avg_len < 40:
        traits.append("tends to give brief, guarded responses")
    elif avg_len > 120:
        traits.append("tends to elaborate and share details openly")

    # Emotional expressiveness
    if num_exclamations >= 3 or any(w in all_text for w in ["cannot believe", "so angry", "hate", "furious", "disgusting"]):
        traits.append("emotionally expressive and intense")
    elif any(w in all_text for w in ["i guess", "maybe", "i don't know", "not sure"]):
        traits.append("uncertain and hesitant")

    # Self-blame vs external attribution
    if any(w in all_text for w in ["my fault", "i should have", "i'm not good enough", "i'm the problem"]):
        traits.append("tends toward self-blame")
    elif any(w in all_text for w in ["they did", "it's unfair", "they don't", "nobody cares"]):
        traits.append("externalizes blame or feels wronged")

    # Action orientation
    if any(w in all_text for w in ["what should i do", "how do i", "i need to", "i want to change"]):
        traits.append("action-oriented, wants concrete solutions")
    elif any(w in all_text for w in ["nothing works", "can't do anything", "hopeless", "no point"]):
        traits.append("feels stuck and helpless")

    # Relationship focus
    if any(w in all_text for w in ["family", "partner", "friend", "mother", "father", "husband", "wife", "boyfriend", "girlfriend"]):
        traits.append("relationship-focused concerns")

    if not traits:
        traits.append("moderate engagement, no strong personality signals")

    return "; ".join(traits[:3])


def load_esconv_profiles(filepath: str, max_profiles: Optional[int] = None) -> List[Dict[str, Any]]:
    """Load client profiles from ESConv.json.

    ESConv.json contains 1300 conversations, each with:
      - experience_type: "Current Experience" or "Previous Experience"
      - emotion_type: e.g. "anxiety", "sadness", "anger"
      - problem_type: e.g. "job crisis", "academic pressure"
      - situation: one-sentence description of the client's problem
      - dialog: the original ESConv conversation turns

    We extract persona fields, the first few seeker utterances as background,
    and infer personality traits from communication style.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    profiles: List[Dict[str, Any]] = []
    for i, item in enumerate(data):
        if max_profiles and len(profiles) >= max_profiles:
            break

        # Collect all seeker lines for personality inference
        seeker_lines = []
        for turn in item.get("dialog", []):
            if turn.get("speaker") == "seeker":
                seeker_lines.append(turn["content"].strip())

        personality = _infer_personality(seeker_lines)
        background_sample = " ".join(seeker_lines[:3])

        profiles.append({
            "index": i,
            "experience_type": item.get("experience_type", ""),
            "emotion_type": item.get("emotion_type", ""),
            "problem_type": item.get("problem_type", ""),
            "situation": item.get("situation", ""),
            "seeker_background": background_sample,
            "personality": personality,
            "cooperation_level": 2,
        })

    return profiles


class ClientSimulator:
    """Simulates a therapy client using an LLM."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str = "google/gemini-2.5-flash",
        language: str = "en",
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.language = language

    def generate_response(
        self,
        profile: Dict[str, Any],
        history: List[Dict[str, str]],
        therapist_message: str,
    ) -> str:
        cooperation_level = profile.get("cooperation_level", 2)
        cooperation_desc = COOPERATION_LEVELS.get(cooperation_level, COOPERATION_LEVELS[2])

        template = CLIENT_SYSTEM_PROMPT_ZH if self.language == "zh" else CLIENT_SYSTEM_PROMPT_EN
        system_prompt = template.format(
            emotion_type=profile.get("emotion_type", "distressed"),
            problem_type=profile.get("problem_type", "personal challenge"),
            situation=profile.get("situation", "facing difficulties"),
            personality=profile.get("personality", ""),
            seeker_background=profile.get("seeker_background", ""),
            cooperation_level=cooperation_level,
            cooperation_desc=cooperation_desc,
        )

        messages = [{"role": "system", "content": system_prompt}]
        for turn in history:
            messages.append({"role": "assistant", "content": turn["therapist"]})
            messages.append({"role": "user", "content": turn["client"]})

        if therapist_message:
            messages.append({"role": "assistant", "content": therapist_message})

        messages.append({"role": "user", "content": "（请以来访者身份回复）" if self.language == "zh" else "(Respond as the client)"})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.9,
                max_tokens=150,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [ERROR] Client LLM failed: {e}")
            return "..." if self.language == "zh" else "I don't know what to say."

    def generate_opening(self, profile: Dict[str, Any]) -> str:
        """Generate the client's opening message."""
        cooperation_level = profile.get("cooperation_level", 2)
        cooperation_desc = COOPERATION_LEVELS.get(cooperation_level, COOPERATION_LEVELS[2])

        template = CLIENT_SYSTEM_PROMPT_ZH if self.language == "zh" else CLIENT_SYSTEM_PROMPT_EN
        system_prompt = template.format(
            emotion_type=profile.get("emotion_type", "distressed"),
            problem_type=profile.get("problem_type", "personal challenge"),
            situation=profile.get("situation", "facing difficulties"),
            personality=profile.get("personality", ""),
            seeker_background=profile.get("seeker_background", ""),
            cooperation_level=cooperation_level,
            cooperation_desc=cooperation_desc,
        )

        if self.language == "zh":
            prompt = "你刚开始和咨询师对话。用一两句话描述你来这里的原因或当前的感受。"
        else:
            prompt = "You are starting a therapy session. In 1-2 sentences, describe why you're here or how you're feeling."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.9,
                max_tokens=100,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"  [ERROR] Opening generation failed: {e}")
            return profile.get("situation", "I'm not doing well lately.")


class INTClient:
    """Communicates with the INT API via SSE."""

    def __init__(self, api_url: str = "http://127.0.0.1:8000"):
        self.api_url = api_url.rstrip("/")
        self.http = httpx.Client(timeout=120.0)

    def send_message(
        self,
        message: str,
        session_id: str,
        participant_id: str,
        language: str = "en",
    ) -> Dict[str, Any]:
        """Send a message and collect the full SSE response."""
        url = f"{self.api_url}/api/chat"
        payload = {
            "session_id": session_id,
            "message": message,
            "participant_id": participant_id,
            "language": language,
        }

        full_response = ""
        stage = ""
        reflection_level = ""

        with self.http.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if data.get("done"):
                    stage = data.get("stage", "")
                    reflection_level = data.get("reflection_level", "")
                    if data.get("error"):
                        print(f"  [WARN] Server error: {data['error']}")
                elif "token" in data:
                    full_response += data["token"]

        return {
            "therapist": full_response,
            "stage": stage,
            "reflection_level": reflection_level,
        }

    def check_health(self) -> bool:
        try:
            r = self.http.get(f"{self.api_url}/health")
            return r.status_code == 200
        except Exception:
            return False


def run_simulation(
    profile: Dict[str, Any],
    client_sim: ClientSimulator,
    int_client: INTClient,
    num_turns: int = 35,
    language: str = "en",
    quiet: bool = False,
) -> Dict[str, Any]:
    """Run a full simulation and return the dialogue record."""
    session_id = str(uuid.uuid4())
    profile_label = f"{profile.get('emotion_type','x')}_{profile.get('problem_type','x')}"
    participant_id = f"sim_{profile_label[:30]}_{session_id[:8]}"

    dialogue: List[Dict[str, Any]] = []
    history: List[Dict[str, str]] = []

    if not quiet:
        print(f"  Session: {session_id}")
        print(f"  Profile: {profile.get('emotion_type', '?')} / {profile.get('problem_type', '?')}")
        print(f"  Cooperation: {profile.get('cooperation_level', 2)}")

    for turn_num in range(1, num_turns + 1):
        # Generate client message
        if turn_num == 1:
            client_msg = client_sim.generate_opening(profile)
        else:
            last_therapist = history[-1]["therapist"] if history else ""
            client_msg = client_sim.generate_response(profile, history, last_therapist)

        if not quiet:
            print(f"  [{turn_num:02d}] Client: {client_msg[:60]}{'...' if len(client_msg) > 60 else ''}")

        # Send to INT
        try:
            result = int_client.send_message(
                message=client_msg,
                session_id=session_id,
                participant_id=participant_id,
                language=language,
            )
        except Exception as e:
            print(f"  [ERROR] INT API failed at turn {turn_num}: {e}")
            break

        therapist_msg = result["therapist"]
        if not quiet:
            print(f"       AI: {therapist_msg[:60]}{'...' if len(therapist_msg) > 60 else ''}")

        turn_record = {
            "round": turn_num,
            "client": client_msg,
            "therapist": therapist_msg,
            "stage": result["stage"],
            "reflection_level": result["reflection_level"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        dialogue.append(turn_record)
        history.append({"client": client_msg, "therapist": therapist_msg})

    return {
        "session_id": session_id,
        "participant_id": participant_id,
        "profile": {
            "index": profile.get("index", -1),
            "emotion_type": profile.get("emotion_type", ""),
            "problem_type": profile.get("problem_type", ""),
            "situation": profile.get("situation", ""),
            "cooperation_level": profile.get("cooperation_level", 2),
        },
        "settings": {
            "language": language,
            "client_model": client_sim.model,
            "num_turns": num_turns,
        },
        "dialogue": dialogue,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Simulate ESConv client profiles interacting with INT system"
    )
    parser.add_argument("--esconv", type=str, help="Path to ESConv.json (1300 profiles)")
    parser.add_argument("--profile-index", type=int, default=None, help="Run a single profile by index (0-1299)")
    parser.add_argument("--turns", type=int, default=35, help="Number of dialogue turns (default: 35)")
    parser.add_argument("--language", type=str, default="en", choices=["en", "zh"], help="Language (default: en)")
    parser.add_argument("--cooperation-level", type=int, default=None, help="Override cooperation level (0-4)")
    parser.add_argument("--api-url", type=str, default="http://127.0.0.1:8000", help="INT API URL")
    parser.add_argument("--client-model", type=str, default="google/gemini-2.5-flash", help="Client simulation model")
    parser.add_argument("--output-dir", type=str, default="./simulation_output", help="Output directory")
    parser.add_argument("--max-profiles", type=int, default=None, help="Max profiles to process in batch mode")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-turn output")

    args = parser.parse_args()

    if not args.esconv:
        default_path = Path(__file__).parent.parent / "data" / "esconv_profiles" / "ESConv.json"
        if default_path.exists():
            args.esconv = str(default_path)
        else:
            parser.error("Provide --esconv path to ESConv.json")

    # Load API key from .env
    env_path = Path(__file__).parent / ".env"
    api_key = ""
    base_url = "https://openrouter.ai/api/v1"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("OPENROUTER_BASE_URL="):
                base_url = line.split("=", 1)[1].strip().strip('"').strip("'")

    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not found in .env")
        sys.exit(1)

    # Initialize components
    int_client = INTClient(api_url=args.api_url)
    if not int_client.check_health():
        print(f"[ERROR] INT server not reachable at {args.api_url}")
        sys.exit(1)
    print(f"[OK] INT server connected at {args.api_url}")

    client_sim = ClientSimulator(
        api_key=api_key,
        base_url=base_url,
        model=args.client_model,
        language=args.language,
    )

    # Collect profiles from ESConv.json
    profiles = load_esconv_profiles(args.esconv, max_profiles=args.max_profiles)
    if args.profile_index is not None:
        if 0 <= args.profile_index < len(profiles):
            profiles = [profiles[args.profile_index]]
        else:
            print(f"[ERROR] --profile-index {args.profile_index} out of range (0-{len(profiles)-1})")
            sys.exit(1)

    if not profiles:
        print("[ERROR] No profiles found")
        sys.exit(1)

    # Override cooperation level if specified
    if args.cooperation_level is not None:
        for p in profiles:
            p["cooperation_level"] = args.cooperation_level

    # Run simulations
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"\nRunning {len(profiles)} simulation(s), {args.turns} turns each\n")

    for i, profile in enumerate(profiles):
        print(f"[{i+1}/{len(profiles)}] #{profile.get('index',0)} {profile.get('emotion_type','')} / {profile.get('problem_type','')}")
        t0 = time.time()

        result = run_simulation(
            profile=profile,
            client_sim=client_sim,
            int_client=int_client,
            num_turns=args.turns,
            language=args.language,
            quiet=args.quiet,
        )

        elapsed = time.time() - t0
        actual_turns = len(result["dialogue"])
        print(f"  Done: {actual_turns} turns in {elapsed:.1f}s")

        # Save output
        out_filename = f"{profile.get('index',0):04d}_{profile.get('emotion_type','x')}_{profile.get('problem_type','x')}_{result['session_id'][:8]}.json"
        out_path = os.path.join(args.output_dir, out_filename)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"  Saved: {out_path}\n")

    print("All simulations complete.")


if __name__ == "__main__":
    main()
