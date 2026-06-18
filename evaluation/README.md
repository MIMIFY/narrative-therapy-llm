# Evaluation

[English](README.md) | [Chinese](README_zh.md)

This directory contains two evaluation pipelines for INT dialogues.

Paper: https://aclanthology.org/2025.emnlp-main.1245/

- `ima/`: Innovative Moment Assessment / IMCS annotation for client turns.
- `dimension_metrics/`: LLM-based multi-dimensional therapeutic quality scoring.

Both pipelines work with INT simulation outputs and exported sessions.

## Input Format

The recommended format is a JSON list of dialogue turns.

```json
[
  {
    "round": 1,
    "client": "I feel overwhelmed...",
    "therapist": "That sounds heavy...",
    "stage": "Trust Building",
    "reflection_level": "Empathic Comforting"
  }
]
```

The scripts also support INT simulation files in the wrapped format:

```json
{
  "session_id": "...",
  "dialogue": [
    {"round": 1, "client": "...", "therapist": "..."}
  ]
}
```

Fallback readers are included for older fields such as `user`, `baseline`, `answer_final`, and `answer_before`.

## Install

```bash
cd evaluation
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Set credentials for an OpenAI-compatible API.

```bash
export OPENAI_API_KEY=your-key
export OPENAI_BASE_URL=https://api.openai.com/v1
```

For OpenRouter:

```bash
export OPENROUTER_API_KEY=your-key
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

## Input Layouts

Flat layout:

```text
int/simulation_output/
├── dialogue_001.json
└── dialogue_002.json
```

Use `--version .`.

Versioned layout:

```text
outputs/
├── GPT-4o/
│   ├── dialogue_001.json
│   └── dialogue_002.json
└── INT/
    └── dialogue_001.json
```

Use `--input_dir outputs --version GPT-4o`.

## IMA / IMCS Annotation

Run from `evaluation/ima`.

```bash
cd ima
../venv/bin/python IMCS_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/imcs \
  --number INT-full \
  --language en
```

Common options:

- `--language zh|en`: prompt language.
- `--context_window 5`: previous turns used as annotation context.
- `--max_files 10`: quick smoke run.
- `--specific_prefix 2`: process files whose names start with `cooperation_level_2_`.
- `--engine gpt-4o`: OpenAI-compatible model name.
- `--base_url`: override provider URL.
- `--api_key`: override environment API key.

Output layout:

```text
outputs/imcs/
└── flat/
    └── INT-full/
        ├── dialogue_001.json
        └── ...
```

Each turn receives an `IMCS` object with `annotation`, `resource`, `confidence`, and `latent_narrative_dynamics_analysis`.

## IMA Analysis

After annotation, `ima/Analysis.py` can summarize and plot IMCS category salience.

```bash
../venv/bin/python Analysis.py \
  --input_dir ../outputs/imcs/flat/INT-full \
  --output_dir ../outputs/imcs_analysis
```

## Therapeutic Dimension Metrics

Run from `evaluation/dimension_metrics`.

```bash
cd ../dimension_metrics
../venv/bin/python dimention_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/dimensions \
  --number INT-full \
  --key_client client \
  --key_therapist therapist
```

Or use the wrapper:

```bash
OPENAI_API_KEY=your-key ./run_evaluation.sh
```

Common options:

- `--key_client client`: JSON key for the client utterance.
- `--key_therapist therapist`: JSON key for the therapist response.
- `--specific_prefix cooperation_level_2`: process matching files only.
- `--max_files 10`: quick smoke run.
- `--engine gpt-4o`: OpenAI-compatible model name.

Output layout:

```text
outputs/dimensions/
└── flat/
    └── INT-full/
        ├── all_evaluation_results.json
        └── average_scores_all.json
```

## Notes for Reproducibility

- These scripts call external LLMs, so scores can vary across providers, models, and dates.
- Use fixed model names and record `base_url`, `engine`, and date for reproducible experiments.
