#!/usr/bin/env bash
set -euo pipefail

# Example batch runner for therapeutic dimension evaluation.
# Configure credentials through environment variables; never commit API keys.
#
# Required:
#   OPENAI_API_KEY or OPENROUTER_API_KEY
#
# Optional:
#   OPENAI_BASE_URL or OPENROUTER_BASE_URL
#   INPUT_DIR, OUTPUT_DIR, ENGINE, VERSION, NUMBER, KEY_CLIENT, KEY_THERAPIST

INPUT_DIR="${INPUT_DIR:-../../int/simulation_output}"
OUTPUT_DIR="${OUTPUT_DIR:-./evaluation_results}"
ENGINE="${ENGINE:-gpt-4o}"
BASE_URL="${OPENAI_BASE_URL:-${OPENROUTER_BASE_URL:-https://api.openai.com/v1}}"
API_KEY="${OPENAI_API_KEY:-${OPENROUTER_API_KEY:-}}"
VERSION="${VERSION:-.}"
NUMBER="${NUMBER:-INT-full}"
KEY_CLIENT="${KEY_CLIENT:-client}"
KEY_THERAPIST="${KEY_THERAPIST:-therapist}"

if [ -z "$API_KEY" ]; then
  echo "Error: set OPENAI_API_KEY or OPENROUTER_API_KEY before running evaluation." >&2
  exit 1
fi

python dimention_metrics.py \
  --input_dir "$INPUT_DIR" \
  --output_dir "$OUTPUT_DIR" \
  --version "$VERSION" \
  --number "$NUMBER" \
  --engine "$ENGINE" \
  --api_key "$API_KEY" \
  --base_url "$BASE_URL" \
  --key_client "$KEY_CLIENT" \
  --key_therapist "$KEY_THERAPIST"
