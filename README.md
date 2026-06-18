# Reframe Your Life Story: Interactive Narrative Therapist and Innovative Moment Assessment with Large Language Models

[English](README.md) | [Chinese](README_zh.md)

Official code and data for the EMNLP 2025 paper.

Paper: https://aclanthology.org/2025.emnlp-main.1245/

> This repository is for research use only. It is not a substitute for professional mental health care.

## Overview

This repository contains three public parts:

- `int/`: a locally runnable Interactive Narrative Therapist (INT), including a FastAPI backend, web UI, RAG, session memory, personal story cards, and researcher dashboard.
- `evaluation/`: scripts for Innovative Moment Assessment (IMA/IMCS) and therapeutic dimension scoring.
- `data/`: released NTConv data and ESConv-derived profile seeds.

## Demo Video

https://github.com/user-attachments/assets/3240ae8f-9e38-4ff1-8300-7c6ddd63f5c6

## Repository Structure

```text
.
├── int/
│   ├── backend/                  # INT orchestration, RAG, memory, API routes
│   ├── backend/knowledge/        # 13 Markdown RAG knowledge files
│   ├── frontend/                 # participant UI and researcher dashboard
│   ├── simulate_client.py        # automatic client simulation
│   ├── README.md                 # English
│   └── README_zh.md              # Chinese
├── evaluation/
│   ├── ima/                      # IMA / IMCS annotation
│   ├── dimension_metrics/        # therapeutic dimension scoring
│   ├── README.md                 # English
│   └── README_zh.md              # Chinese
├── data/
│   ├── esconv_profiles/
│   ├── ntconv/
│   ├── README.md                 # English
│   └── README_zh.md              # Chinese
└── README.md
```

## Quick Start: Run INT

Prerequisites:

- Python 3.10+
- An OpenRouter API key, or another OpenAI-compatible provider configured in `.env`
- Network access on the first RAG build, because the BGE-M3 embedding model is downloaded from HuggingFace
- About 600 MB of disk space for the embedding model, plus local Chroma index files

### 1. Install dependencies

```bash
cd int
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Configure models

```bash
cp .env.example .env
```

Edit `int/.env` and set your OpenRouter API key:

```text
OPENROUTER_API_KEY=your-key
```

You can also change `STAGE_PLANNER_MODEL`, `REFLECTION_PLANNER_MODEL`, `RESPONSE_MODEL`, and `GOAL_CHECKER_MODEL`.

### 3. Build the RAG index

INT uses 13 Markdown question-bank files under `int/backend/knowledge/`.
The first run downloads the BGE-M3 embedding model and builds a local Chroma index.
This can take several minutes depending on network speed and machine performance.

```bash
venv/bin/python backend/scripts/reindex_rag.py --force
```

Expected dry-run counts after the knowledge files are loaded:

```text
Knowledge files loaded: 13
Question documents parsed: 366
Collection: therapy_questions
```

Dry run without rebuilding:

```bash
venv/bin/python backend/scripts/reindex_rag.py
```

For a backend smoke test without RAG or embedding downloads, set `DISABLE_RAG=1` in `int/.env`.
Therapeutic responses will still run, but RAG exemplar retrieval will be skipped.

### 4. Start the server

```bash
venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open the participant UI:

```text
http://127.0.0.1:8000
```

Open the researcher dashboard:

```text
http://127.0.0.1:8000/admin.html
```

Set `ADMIN_KEY` in `.env`. The example/default local admin key is `change-me-before-running-admin`; keep it only for local testing and change it before sharing or deployment.

## INT Pipeline

```text
User input
  -> Stage Planner
  -> Reflection Planner
  -> RAG retrieval over 13 knowledge files
  -> Memory context retrieval
  -> Streaming response generation
  -> Async goal check
  -> Memory update every N turns
```

| Stage | Reflection levels |
| --- | --- |
| Trust Building | Exploring the Problem Event; Empathic Comforting |
| Problem Externalization | Negotiation of the Dominant Problem; Mapping Problem Effects; Evaluating Problem Effects; Justification of Evaluation |
| Re-authoring | Elaboration of Unique Outcomes; Exploration of Identity Landscape; Exploration of Action Landscape |
| Re-membering | Significant Others' Contributions; Self through Others; One's Contributions; Implications for Identity |

## RAG Knowledge Updates

RAG source files:

```text
int/backend/knowledge/
```

The indexer only includes files registered in:

```text
int/backend/core/stages.py
KNOWLEDGE_FILE_MAP
```

To update RAG:

1. Edit an existing `.md` file, or add a new file under `int/backend/knowledge/`.
2. If adding a file, register it in `KNOWLEDGE_FILE_MAP` with the correct `stage` and `level`.
3. Rebuild the index.

```bash
cd int
venv/bin/python backend/scripts/reindex_rag.py --force
```

`int/chroma_db/` is the generated local vector index.

When adding or changing knowledge files, run `venv/bin/python backend/scripts/reindex_rag.py --force` again before starting the server.

## Memory and Story Cards

Runtime state is stored in local SQLite:

```text
int/sessions.db
```

Memory behavior:

- Conversation history is stored per session.
- Researcher traces include stage, reflection level, RAG hits, model names, goal-check output, and memory-update status.
- Long-term participant memory is updated every `MEMORY_UPDATE_INTERVAL` turns, default `5`.
- Personal story cards become available after `STORY_MIN_TURNS`, default `20`.
- Opening "My Story" shows history first; generation requires a separate click.

`int/sessions.db` and `int/memory_chroma_db/` are local runtime files that may contain participant data.

## Simulate Dialogues

Use `simulate_client.py` with `data/esconv_profiles/ESConv.json`.

Single profile:

```bash
cd int
venv/bin/python simulate_client.py \
  --esconv ../data/esconv_profiles/ESConv.json \
  --profile-index 42 \
  --turns 35 \
  --language en \
  --output-dir ./simulation_output
```

Batch mode:

```bash
venv/bin/python simulate_client.py \
  --esconv ../data/esconv_profiles/ESConv.json \
  --max-profiles 10 \
  --turns 35 \
  --language en \
  --output-dir ./simulation_output
```

Simulation outputs are compatible with the evaluation scripts.

## Run Evaluation

Install evaluation dependencies:

```bash
cd evaluation
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Set an OpenAI-compatible API key:

```bash
export OPENAI_API_KEY=your-key
export OPENAI_BASE_URL=https://api.openai.com/v1
```

For OpenRouter, use `OPENROUTER_API_KEY` and `OPENROUTER_BASE_URL`.

### IMA / IMCS Annotation

```bash
cd ima
../venv/bin/python IMCS_metrics.py \
  --input_dir ../../int/simulation_output \
  --version . \
  --output_dir ../outputs/imcs \
  --number INT-full \
  --language en
```

For Chinese dialogues, use `--language zh`.

### Therapeutic Dimension Metrics

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

Wrapper script:

```bash
OPENAI_API_KEY=your-key ./run_evaluation.sh
```

See `evaluation/README.md` for details.

## Data

`data/ntconv/` contains 1300 English narrative therapy dialogues, split into train/test.

`data/esconv_profiles/ESConv.json` contains 1300 ESConv-derived client profile seeds for simulation.

## Citation

Paper: https://aclanthology.org/2025.emnlp-main.1245/

```bibtex
@inproceedings{feng2025reframe,
  title={Reframe Your Life Story: Interactive Narrative Therapist and Innovative Moment Assessment with Large Language Models},
  author={Feng, Yi and Wang, Jiaqi and Zhang, Wenxuan and Chen, Zhuang and Yutong, Shen and Xiao, Xiyao and Huang, Minlie and Jing, Liping and Yu, Jian},
  booktitle={Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing},
  pages={24495--24520},
  year={2025}
}
```

## Contact

Yi Feng: yifeng@bjtu.edu.cn
